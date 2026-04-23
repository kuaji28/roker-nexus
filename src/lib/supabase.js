import { createClient } from '@supabase/supabase-js'

export const supabase = createClient(
  import.meta.env.VITE_SUPABASE_URL,
  import.meta.env.VITE_SUPABASE_ANON_KEY
)

async function sha256(text) {
  const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text))
  return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2, '0')).join('')
}

export async function loginUsuario(nombre, pin) {
  const hash = await sha256(pin)
  const { data, error } = await supabase
    .from('perfiles')
    .select('id, nombre, email, rol, activo')
    .ilike('nombre', nombre.trim())
    .eq('pin_hash', hash)
    .eq('activo', true)
    .single()
  if (error || !data) throw new Error('Usuario o PIN incorrecto')
  return data
}

export async function updatePinUsuario(userId, nuevoPin) {
  const hash = await sha256(nuevoPin)
  const { error } = await supabase
    .from('perfiles')
    .update({ pin_hash: hash })
    .eq('id', userId)
  if (error) throw error
}

export async function getPin() {
  const { data } = await supabase
    .from('config')
    .select('valor')
    .eq('clave', 'pin_requirement')
    .single()
  if (!data) return null
  try { return JSON.parse(data.valor)?.pin ?? null } catch { return null }
}

export async function getStats() {
  const { data } = await supabase
    .from('vehiculos')
    .select('estado, precio_base')
  if (!data) return {}
  const total       = data.length
  const disponible  = data.filter(v => v.estado === 'disponible').length
  const seniado     = data.filter(v => v.estado === 'señado').length
  const en_revision = data.filter(v => v.estado === 'en_revision').length
  const vendido     = data.filter(v => v.estado === 'vendido').length
  return { total, disponible, seniado, en_revision, vendido }
}

export async function getVehiculos({ estado, tipo, search } = {}) {
  let q = supabase
    .from('vehiculos')
    .select('id,tipo,marca,modelo,anio,version,km_hs,precio_base,estado,patente,color,combustible,transmision')
    .order('created_at', { ascending: false })

  if (estado && estado !== 'todos') q = q.eq('estado', estado)
  if (tipo   && tipo   !== 'todos') q = q.eq('tipo', tipo)
  if (search) q = q.or(`marca.ilike.%${search}%,modelo.ilike.%${search}%,patente.ilike.%${search}%`)

  const { data } = await q
  return data || []
}

export async function getVehiculo(id) {
  const [{ data: v }, { data: medias }] = await Promise.all([
    supabase.from('vehiculos').select('*').eq('id', id).single(),
    supabase.from('medias').select('*').eq('vehiculo_id', id).order('orden'),
  ])
  return { vehiculo: v, medias: medias || [] }
}

// ── Vehiculos CRUD ───────────────────────────────────────────────
export async function createVehiculo(data) {
  const { data: v, error } = await supabase
    .from('vehiculos')
    .insert([{ ...data, estado: data.estado || 'disponible', fecha_ingreso: new Date().toISOString().split('T')[0] }])
    .select()
    .single()
  if (error) throw error
  return v
}

export async function updateVehiculo(id, data) {
  const { error } = await supabase
    .from('vehiculos')
    .update({ ...data, updated_at: new Date().toISOString() })
    .eq('id', id)
  if (error) throw error
}

// ── Fotos ────────────────────────────────────────────────────────
export async function uploadFoto(vehiculoId, file) {
  const path = `${vehiculoId}/${Date.now()}-${file.name.replace(/\s+/g, '_')}`
  const { data, error } = await supabase.storage
    .from('vehiculos-fotos')
    .upload(path, file, { contentType: file.type, upsert: false })
  if (error) throw error
  const { data: { publicUrl } } = supabase.storage
    .from('vehiculos-fotos')
    .getPublicUrl(data.path)
  const { error: mediaErr } = await supabase.from('medias').insert([{
    vehiculo_id: vehiculoId, tipo: 'foto', url: publicUrl, orden: 0
  }])
  if (mediaErr) console.warn('uploadFoto: foto subida pero no registrada en medias', mediaErr)
  return publicUrl
}

export async function deleteFoto(mediaId, storagePath) {
  if (storagePath) {
    await supabase.storage.from('vehiculos-fotos').remove([storagePath])
  }
  await supabase.from('medias').delete().eq('id', mediaId)
}

// ── Vendedores ───────────────────────────────────────────────────
export async function getVendedores() {
  const { data } = await supabase
    .from('vendedores')
    .select('id, nombre, email, telefono, activo, created_at')
    .order('nombre')
  return data || []
}

export async function createVendedor(data) {
  const { error } = await supabase.from('vendedores').insert([data])
  if (error) throw error
}

export async function updateVendedor(id, data) {
  const { error } = await supabase.from('vendedores').update(data).eq('id', id)
  if (error) throw error
}

// ── Ventas ───────────────────────────────────────────────────────
export async function getVentas() {
  const { data } = await supabase
    .from('con_ventas')
    .select('*, vehiculos(marca, modelo, anio, patente), vendedores(nombre)')
    .order('fecha_venta', { ascending: false })
    .limit(100)
  return data || []
}

export async function createVenta(venta) {
  const { data, error } = await supabase
    .from('con_ventas')
    .insert([{ ...venta, fecha_venta: new Date().toISOString().split('T')[0] }])
    .select()
    .single()
  if (error) throw error
  try {
    await updateVehiculo(venta.vehiculo_id, { estado: 'vendido' })
  } catch (e) {
    console.error('createVenta: venta registrada pero estado vehiculo no actualizado', e)
  }
  return data
}

// ── Reportes ─────────────────────────────────────────────────────
export async function getReportes() {
  const now = new Date()
  const firstDay = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().split('T')[0]

  const [{ data: ventas }, { data: todos }, { data: prospectos }] = await Promise.all([
    supabase.from('con_ventas').select('precio_final, fecha_venta, moneda_precio').gte('fecha_venta', firstDay),
    supabase.from('vehiculos').select('estado, precio_base, costo_compra, fecha_ingreso'),
    supabase.from('prospectos').select('estado, created_at').gte('created_at', firstDay),
  ])

  const ventasMes  = (ventas || []).length
  const ingresoUSD = (ventas || []).reduce((s, v) => s + (Number(v.precio_final) || 0), 0)
  const disponibles = (todos || []).filter(v => v.estado === 'disponible')
  const stockUSD   = disponibles.reduce((s, v) => s + (Number(v.precio_base) || 0), 0)
  const ingresosMes = (todos || []).filter(v => v.fecha_ingreso >= firstDay).length
  const leadsNuevos = (prospectos || []).length

  const months = []
  for (let i = 5; i >= 0; i--) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1)
    months.push({
      label: d.toLocaleDateString('es-AR', { month: 'short' }),
      from: d.toISOString().split('T')[0],
      to: new Date(d.getFullYear(), d.getMonth() + 1, 0).toISOString().split('T')[0],
    })
  }

  const { data: hist } = await supabase
    .from('con_ventas').select('fecha_venta, precio_final').gte('fecha_venta', months[0].from)

  const bars = months.map(m => ({
    label: m.label,
    count: (hist || []).filter(v => v.fecha_venta >= m.from && v.fecha_venta <= m.to).length,
    total: (hist || []).filter(v => v.fecha_venta >= m.from && v.fecha_venta <= m.to)
      .reduce((s, v) => s + (Number(v.precio_final) || 0), 0),
  }))

  return { ventasMes, ingresoUSD, stockUSD, ingresosMes, leadsNuevos, bars }
}

// ── Config ───────────────────────────────────────────────────────
export async function updatePin(newPin) {
  const { error } = await supabase
    .from('config')
    .update({ valor: JSON.stringify({ pin: newPin, min_length: 4, max_length: 20 }) })
    .eq('clave', 'pin_requirement')
  if (error) throw error
}

export async function getTC() {
  const { data } = await supabase
    .from('config').select('valor').eq('clave', 'tipo_cambio').single()
  if (data) {
    try { return Number(JSON.parse(data.valor)?.valor) || 1415 } catch { return 1415 }
  }
  return 1415
}

export async function updateTC(valor) {
  const { error } = await supabase
    .from('config')
    .upsert({ clave: 'tipo_cambio', valor: JSON.stringify({ valor }) }, { onConflict: 'clave' })
  if (error) throw error
}

// ── Cobranza ─────────────────────────────────────────────────────
export async function getFinanciamientos() {
  const { data } = await supabase
    .from('financiamientos')
    .select('*, vehiculos(marca, modelo, anio)')
    .order('created_at', { ascending: false })
  return data || []
}

export async function getCuotasVencidas() {
  const hoy = new Date().toISOString().split('T')[0]
  const { data } = await supabase
    .from('cuotas')
    .select('*, financiamientos(deudor_nombre, vehiculos(marca, modelo, anio))')
    .lt('fecha_vencimiento', hoy)
    .eq('estado', 'pendiente')
    .order('fecha_vencimiento')
  return data || []
}

// ── Prospectos (Leads) ────────────────────────────────────────
export async function getProspectos({ estado } = {}) {
  let q = supabase
    .from('prospectos')
    .select('*, vehiculos(marca, modelo, anio), vendedores(nombre)')
    .order('created_at', { ascending: false })
  if (estado) q = q.eq('estado', estado)
  const { data } = await q
  return data || []
}

export async function createProspecto(data) {
  const { error } = await supabase.from('prospectos').insert([data])
  if (error) throw error
}

export async function updateProspecto(id, data) {
  const { error } = await supabase.from('prospectos').update(data).eq('id', id)
  if (error) throw error
}

// ── Clientes ──────────────────────────────────────────────────
export async function getClientes({ search } = {}) {
  let q = supabase
    .from('clientes')
    .select('id, nombre, dni, telefono, email, whatsapp, localidad, activo, created_at')
    .order('nombre')
  if (search) q = q.or(`nombre.ilike.%${search}%,dni.ilike.%${search}%,telefono.ilike.%${search}%`)
  const { data } = await q
  return data || []
}

export async function getCliente(id) {
  const { data } = await supabase.from('clientes').select('*').eq('id', id).single()
  return data
}

export async function createCliente(data) {
  const { data: c, error } = await supabase.from('clientes').insert([data]).select().single()
  if (error) throw error
  return c
}

export async function updateCliente(id, data) {
  const { error } = await supabase.from('clientes').update(data).eq('id', id)
  if (error) throw error
}

// ── Gastos de vehículo ────────────────────────────────────────
export async function getGastosByVehiculo(vehiculoId) {
  const { data } = await supabase
    .from('gastos_vehiculo')
    .select('*')
    .eq('vehiculo_id', vehiculoId)
    .order('fecha_gasto', { ascending: false })
  return data || []
}

export async function createGasto(data) {
  const { error } = await supabase.from('gastos_vehiculo').insert([data])
  if (error) throw error
}

// ── Reservas ──────────────────────────────────────────────────
export async function getReservasByVehiculo(vehiculoId) {
  const { data } = await supabase
    .from('reservas')
    .select('*')
    .eq('vehiculo_id', vehiculoId)
    .order('created_at', { ascending: false })
  return data || []
}

export async function createReserva(data) {
  const { error } = await supabase.from('reservas').insert([data])
  if (error) throw error
}

export async function updateReserva(id, data) {
  const { error } = await supabase.from('reservas').update(data).eq('id', id)
  if (error) throw error
}

// ── Gastos global ─────────────────────────────────────────────
export async function getGastosGlobal({ desde, hasta, tipo } = {}) {
  let q = supabase.from('gastos_vehiculo').select('*').order('fecha_gasto', { ascending: false }).limit(500)
  if (desde) q = q.gte('fecha_gasto', desde)
  if (hasta) q = q.lte('fecha_gasto', hasta)
  if (tipo && tipo !== 'todos') q = q.eq('tipo', tipo)
  const { data } = await q
  return data || []
}

export async function getVehiculosConCostos() {
  const { data } = await supabase
    .from('vehiculos')
    .select('id, marca, modelo, anio, estado, costo_compra, precio_base, gastos_total_ars, gastos_total_usd, fecha_ingreso, created_at')
    .order('created_at', { ascending: false })
  return data || []
}

export async function updateVehiculoGastos(id, { gastos_total_ars, gastos_total_usd } = {}) {
  const upd = {}
  if (gastos_total_ars !== undefined) upd.gastos_total_ars = gastos_total_ars
  if (gastos_total_usd !== undefined) upd.gastos_total_usd = gastos_total_usd
  const { error } = await supabase.from('vehiculos').update(upd).eq('id', id)
  if (error) throw error
}

// ── Rotación ──────────────────────────────────────────────────
export async function getVehiculosEnStock() {
  const { data } = await supabase
    .from('vehiculos')
    .select('id, marca, modelo, anio, version, color, km_hs, estado, tipo, patente, precio_base, costo_compra, gastos_total_usd, fecha_ingreso, created_at')
    .neq('estado', 'vendido')
    .order('fecha_ingreso', { ascending: true })
  return data || []
}

// ── Reservas — cancelar activas de un vehículo ───────────────
export async function cancelarReservasVehiculo(vehiculoId) {
  const { error } = await supabase
    .from('reservas')
    .update({ estado: 'cancelada' })
    .eq('vehiculo_id', vehiculoId)
    .eq('estado', 'activa')
  if (error) console.error('cancelarReservasVehiculo:', error)
}

// ── Cobranza — marcar cuota pagada ────────────────────────────
export async function pagarCuota(cuotaId) {
  const { error } = await supabase
    .from('cuotas')
    .update({ estado: 'pagada', fecha_pago: new Date().toISOString().split('T')[0] })
    .eq('id', cuotaId)
  if (error) throw error
}

export async function pagarCuotaConMetadata(cuotaId, { monto_pagado, forma_cobro, moneda_cobro, tc_cobro, notas_cobro } = {}) {
  const hoy = new Date().toISOString().split('T')[0]
  const upd = { estado: 'pagada', fecha_pago: hoy }
  if (monto_pagado !== undefined) upd.monto_pagado = monto_pagado
  if (forma_cobro)  upd.forma_cobro  = forma_cobro
  if (moneda_cobro) upd.moneda_cobro = moneda_cobro
  if (tc_cobro)     upd.tc_cobro     = tc_cobro
  if (notas_cobro)  upd.notas_cobro  = notas_cobro
  const { error } = await supabase.from('cuotas').update(upd).eq('id', cuotaId)
  if (error) throw error
}

export async function getCuotasProximas(dias = 30) {
  const hoy    = new Date().toISOString().split('T')[0]
  const limite = new Date(Date.now() + dias * 86400000).toISOString().split('T')[0]
  const { data } = await supabase
    .from('cuotas')
    .select('*, financiamientos(deudor_nombre, deudor_telefono, vehiculos(marca, modelo, anio))')
    .gte('fecha_vencimiento', hoy)
    .lte('fecha_vencimiento', limite)
    .eq('estado', 'pendiente')
    .order('fecha_vencimiento')
  return data || []
}

// ── Financiamientos — crear con cuotas ───────────────────────
export async function createFinanciamiento({ vehiculo_id, deudor_nombre, deudor_telefono, monto_total, cantidad_cuotas, fecha_primera_cuota, notas }) {
  const { data: fin, error } = await supabase
    .from('financiamientos')
    .insert([{ vehiculo_id, deudor_nombre, deudor_telefono: deudor_telefono || null, monto_total, cantidad_cuotas, estado: 'activo', notas: notas || null }])
    .select()
    .single()
  if (error) throw error
  const montoPorCuota = Math.round(monto_total / cantidad_cuotas)
  const cuotas = []
  // Normalizar a medianoche local para evitar bug de zona horaria Argentina
  let fecha
  if (fecha_primera_cuota) {
    const [y, m, d] = fecha_primera_cuota.split('-').map(Number)
    fecha = new Date(y, m - 1, d)
  } else {
    const hoy = new Date()
    fecha = new Date(hoy.getFullYear(), hoy.getMonth(), hoy.getDate())
  }
  for (let i = 0; i < cantidad_cuotas; i++) {
    const iso = `${fecha.getFullYear()}-${String(fecha.getMonth()+1).padStart(2,'0')}-${String(fecha.getDate()).padStart(2,'0')}`
    cuotas.push({ financiamiento_id: fin.id, numero_cuota: i + 1, monto: montoPorCuota, fecha_vencimiento: iso, estado: 'pendiente' })
    fecha = new Date(fecha.getFullYear(), fecha.getMonth() + 1, fecha.getDate())
  }
  const { error: ce } = await supabase.from('cuotas').insert(cuotas)
  if (ce) console.error('createFinanciamiento: cuotas no creadas', ce)
  return fin
}

// ── Documentación ─────────────────────────────────────────────
export async function getDocumentacion(vehiculoId) {
  const { data } = await supabase
    .from('documentacion')
    .select('*')
    .eq('vehiculo_id', vehiculoId)
    .single()
  return data || null
}

export async function upsertDocumentacion(vehiculoId, data) {
  const { error } = await supabase
    .from('documentacion')
    .upsert({ ...data, vehiculo_id: vehiculoId }, { onConflict: 'vehiculo_id' })
  if (error) throw error
}
