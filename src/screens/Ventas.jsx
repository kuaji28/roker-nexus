import { useEffect, useState } from 'react'
import TopBar from '../components/TopBar'
import StateBadge from '../components/StateBadge'
import Icon from '../components/Icon'
import FormField from '../components/FormField'
import { getVehiculos, getVendedores, createVenta, createFinanciamiento, cancelarReservasVehiculo } from '../lib/supabase'
import { useTc } from '../hooks/useTc'

const FORMAS = ['Efectivo', 'Transferencia', 'Efectivo + Transferencia', 'Financiación', 'Parte de pago']

const EMPTY_BUYER = {
  comprador_nombre: '', comprador_dni: '', comprador_telefono: '',
  precio_final: '', moneda_precio: 'USD', forma_pago: 'Efectivo',
  vendedor_id: '', notas: '',
}
const EMPTY_FIN = {
  monto_total: '', cantidad_cuotas: '12', fecha_primera_cuota: '',
}

export default function Ventas({ onLogout }) {
  const TC = useTc()
  const [step, setStep]         = useState(1)
  const [vehiculos, setVehiculos] = useState([])
  const [vendedores, setVendedores] = useState([])
  const [selected, setSelected] = useState(null)
  const [saving, setSaving]     = useState(false)
  const [done, setDone]         = useState(null)
  const [error, setError]       = useState('')
  const [buyer, setBuyer]       = useState(EMPTY_BUYER)
  const [fin, setFin]           = useState(EMPTY_FIN)

  useEffect(() => {
    Promise.all([
      getVehiculos({ estado: 'disponible' }),
      getVehiculos({ estado: 'señado' }),
    ]).then(([disp, senados]) => setVehiculos([...disp, ...senados]))
    getVendedores().then(setVendedores)
  }, [])

  const f  = (k) => (e) => setBuyer(p => ({ ...p, [k]: e.target.value }))
  const ff = (k) => (e) => setFin(p => ({ ...p, [k]: e.target.value }))

  const esFinanciacion = buyer.forma_pago === 'Financiación'
  const precioARS = buyer.precio_final && TC > 0 && buyer.moneda_precio === 'USD'
    ? Number(buyer.precio_final) * TC
    : null

  async function confirm() {
    if (!buyer.comprador_nombre || !buyer.precio_final) {
      setError('Completá nombre del comprador y precio final.')
      return
    }
    if (esFinanciacion && (!fin.monto_total || !fin.cantidad_cuotas)) {
      setError('Completá el monto total y cantidad de cuotas del financiamiento.')
      return
    }
    setSaving(true)
    setError('')
    try {
      const v = await createVenta({
        vehiculo_id:       selected.id,
        vendedor_id:       buyer.vendedor_id || null,
        precio_final:      Number(buyer.precio_final),
        moneda_precio:     buyer.moneda_precio,
        comprador_nombre:  buyer.comprador_nombre,
        comprador_dni:     buyer.comprador_dni || null,
        comprador_telefono: buyer.comprador_telefono || null,
        forma_pago:        buyer.forma_pago,
        notas:             buyer.notas || null,
      })
      await cancelarReservasVehiculo(selected.id)
      if (esFinanciacion) {
        await createFinanciamiento({
          vehiculo_id:         selected.id,
          deudor_nombre:       buyer.comprador_nombre,
          deudor_telefono:     buyer.comprador_telefono || null,
          monto_total:         Number(fin.monto_total),
          cantidad_cuotas:     Number(fin.cantidad_cuotas),
          fecha_primera_cuota: fin.fecha_primera_cuota || null,
          notas:               buyer.notas || null,
        })
      }
      setDone(v)
      setStep(3)
    } catch (e) {
      setError(e.message || 'Error al registrar venta.')
    } finally {
      setSaving(false)
    }
  }

  function resetForm() {
    setStep(1); setSelected(null)
    setBuyer(EMPTY_BUYER); setFin(EMPTY_FIN); setDone(null)
    Promise.all([
      getVehiculos({ estado: 'disponible' }),
      getVehiculos({ estado: 'señado' }),
    ]).then(([disp, senados]) => setVehiculos([...disp, ...senados]))
  }

  if (step === 3 && done) return (
    <div>
      <TopBar onLogout={onLogout} />
      <div className="main" style={{ maxWidth: 540, margin: '60px auto', textAlign: 'center' }}>
        <div style={{ width: 64, height: 64, borderRadius: '50%', background: 'var(--c-success-tint)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px' }}>
          <Icon name="check" size={28} style={{ stroke: 'var(--c-success)' }} />
        </div>
        <h2 style={{ margin: '0 0 8px' }}>Venta registrada</h2>
        <p style={{ color: 'var(--c-fg-2)', margin: '0 0 24px' }}>
          {selected.marca} {selected.modelo} {selected.anio} vendido a <strong>{buyer.comprador_nombre}</strong>
          {esFinanciacion && <><br /><span style={{ fontSize: 13 }}>Financiamiento creado: {fin.cantidad_cuotas} cuotas de {buyer.moneda_precio} {Math.round(Number(fin.monto_total) / Number(fin.cantidad_cuotas)).toLocaleString('es-AR')}</span></>}
        </p>
        <div style={{ display: 'flex', gap: 10, justifyContent: 'center' }}>
          <button className="btn secondary" onClick={resetForm}>Registrar otra venta</button>
          <a className="btn primary" href={`/vehiculo/${selected.id}`}>Ver vehículo</a>
        </div>
      </div>
    </div>
  )

  return (
    <div>
      <TopBar onLogout={onLogout} />
      <div className="main">
        <div className="page-head">
          <div>
            <h1 className="page-title">Registrar venta</h1>
            <p className="page-caption">Paso {step} de 2</p>
          </div>
          <div style={{ flex: 1 }} />
          <div className="seg">
            <button className={step === 1 ? 'on' : ''} onClick={() => step > 1 && setStep(1)}>
              <Icon name="car" size={13} /> Vehículo
            </button>
            <button className={step === 2 ? 'on' : ''} disabled={!selected}>
              <Icon name="users" size={13} /> Comprador
            </button>
          </div>
        </div>

        {error && <div className="banner warning"><Icon name="alert" size={16} />{error}</div>}

        {/* STEP 1: Seleccionar vehículo */}
        {step === 1 && (
          <div>
            <p style={{ color: 'var(--c-fg-2)', marginBottom: 12 }}>Seleccioná el vehículo a vender:</p>
            {vehiculos.length === 0
              ? <div className="banner info"><Icon name="info" size={16} />No hay vehículos disponibles.</div>
              : vehiculos.map(v => (
                <div key={v.id} className="list-row" style={{ cursor: 'pointer' }}
                  onClick={() => { setSelected(v); setBuyer(p => ({ ...p, precio_final: v.precio_base || '' })); setFin(p => ({ ...p, monto_total: v.precio_base || '' })); setStep(2) }}>
                  <div>
                    <div className="v-title">{v.marca} {v.modelo} {v.anio}{v.version ? ` · ${v.version}` : ''}</div>
                    <div className="v-meta">{v.patente || '—'} · #{v.id}</div>
                  </div>
                  <StateBadge estado={v.estado} />
                  <div className="num">{v.km_hs?.toLocaleString('es-AR') || '0'} km</div>
                  <div className="price-cell"><strong>USD {v.precio_base?.toLocaleString('es-AR')}</strong></div>
                  <Icon name="chev-r" size={16} style={{ stroke: 'var(--c-fg-2)', justifySelf: 'end' }} />
                </div>
              ))
            }
          </div>
        )}

        {/* STEP 2: Datos del comprador */}
        {step === 2 && selected && (
          <div>
            <div className="banner info" style={{ marginBottom: 16 }}>
              <Icon name="car" size={16} />
              <span><strong>{selected.marca} {selected.modelo} {selected.anio}</strong> — USD {selected.precio_base?.toLocaleString('es-AR')}</span>
              <button className="btn ghost" style={{ marginLeft: 'auto', padding: '2px 8px' }} onClick={() => setStep(1)}>Cambiar</button>
            </div>

            <div className="card">
              <h4 style={{ margin: '0 0 14px', fontSize: 13, fontWeight: 600, color: 'var(--c-fg-2)', textTransform: 'uppercase', letterSpacing: 1 }}>Datos del comprador</h4>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
                <FormField label="Nombre comprador" required>
                  <input className="input" placeholder="Juan Pérez" value={buyer.comprador_nombre} onChange={f('comprador_nombre')} />
                </FormField>
                <FormField label="DNI">
                  <input className="input" placeholder="12345678" value={buyer.comprador_dni} onChange={f('comprador_dni')} />
                </FormField>
                <FormField label="Teléfono / WhatsApp">
                  <input className="input" placeholder="+54 9 11 1234 5678" value={buyer.comprador_telefono} onChange={f('comprador_telefono')} />
                </FormField>
                <FormField label="Vendedor">
                  <select className="input" value={buyer.vendedor_id} onChange={f('vendedor_id')}>
                    <option value="">Sin asignar</option>
                    {vendedores.map(vn => <option key={vn.id} value={vn.id}>{vn.nombre}</option>)}
                  </select>
                </FormField>
              </div>
            </div>

            <div className="card" style={{ marginTop: 14 }}>
              <h4 style={{ margin: '0 0 14px', fontSize: 13, fontWeight: 600, color: 'var(--c-fg-2)', textTransform: 'uppercase', letterSpacing: 1 }}>Condiciones de venta</h4>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
                <FormField label="Precio final" required>
                  <input className="input" type="number" value={buyer.precio_final} onChange={f('precio_final')} />
                </FormField>
                <FormField label="Moneda">
                  <select className="input" value={buyer.moneda_precio} onChange={f('moneda_precio')}>
                    <option value="USD">USD</option>
                    <option value="ARS">ARS</option>
                  </select>
                </FormField>
                <FormField label="Forma de pago">
                  <select className="input" value={buyer.forma_pago} onChange={f('forma_pago')}>
                    {FORMAS.map(fm => <option key={fm} value={fm}>{fm}</option>)}
                  </select>
                </FormField>
                {precioARS && (
                  <FormField label="Equivalente ARS">
                    <input className="input" readOnly value={`$ ${precioARS.toLocaleString('es-AR', { maximumFractionDigits: 0 })}`} style={{ color: 'var(--c-fg-2)', cursor: 'default' }} />
                  </FormField>
                )}
                <FormField label="Notas" style={{ gridColumn: '1/-1' }}>
                  <textarea className="input" rows={2} value={buyer.notas} onChange={f('notas')} style={{ resize: 'vertical' }} />
                </FormField>
              </div>
            </div>

            {/* Sección de financiamiento */}
            {esFinanciacion && (
              <div className="card" style={{ marginTop: 14, borderLeft: '3px solid var(--c-accent)' }}>
                <h4 style={{ margin: '0 0 14px', fontSize: 13, fontWeight: 600, color: 'var(--c-fg-2)', textTransform: 'uppercase', letterSpacing: 1 }}>
                  <Icon name="card" size={13} /> Plan de cuotas
                </h4>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 14 }}>
                  <FormField label="Monto total a financiar" required>
                    <input className="input" type="number" value={fin.monto_total} onChange={ff('monto_total')} placeholder="USD o ARS" />
                  </FormField>
                  <FormField label="Cantidad de cuotas" required>
                    <input className="input" type="number" value={fin.cantidad_cuotas} onChange={ff('cantidad_cuotas')} min={1} max={120} />
                  </FormField>
                  <FormField label="Fecha 1ª cuota">
                    <input className="input" type="date" value={fin.fecha_primera_cuota} onChange={ff('fecha_primera_cuota')} />
                  </FormField>
                </div>
                {fin.monto_total && fin.cantidad_cuotas && (
                  <div className="banner info" style={{ marginTop: 10 }}>
                    <Icon name="info" size={16} />
                    {fin.cantidad_cuotas} cuotas de <strong>{buyer.moneda_precio} {Math.round(Number(fin.monto_total) / Number(fin.cantidad_cuotas)).toLocaleString('es-AR')}</strong>
                  </div>
                )}
              </div>
            )}

            <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', marginTop: 16 }}>
              <button className="btn secondary" onClick={() => setStep(1)}><Icon name="arrow-l" size={14} /> Atrás</button>
              <button className="btn primary" onClick={confirm} disabled={saving}>
                {saving ? 'Registrando…' : <><Icon name="check" size={14} /> Confirmar venta</>}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
