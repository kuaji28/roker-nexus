import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import TopBar from '../components/TopBar'
import StateBadge, { UBICACION_META, RECON_META } from '../components/StateBadge'
import Icon from '../components/Icon'
import Modal from '../components/Modal'
import FormField from '../components/FormField'
import { getVehiculo, updateVehiculo, getGastosByVehiculo, createGasto, getReservasByVehiculo, createReserva, getDocumentacion, upsertDocumentacion, getHistorialVehiculo, addHistorialEntry, iniciarNegociacion, liberarNegociacion, getVendedores } from '../lib/supabase'
import { useUser } from '../hooks/useUser'
import { callAI, callAIFiles, aiConfigured } from '../lib/api'
import { useTc } from '../hooks/useTc'

// ── Publicar helpers ──────────────────────────────────────────
export function generateChipsFromSpecs(specs = {}) {
  const chips = []
  if (specs.apple_carplay === true)        chips.push('Apple CarPlay')
  if (specs.android_auto === true)         chips.push('Android Auto')
  if (specs.carga_inalambrica === true)    chips.push('Carga inalámbrica')
  if (specs.techo_solar === true)          chips.push('Techo solar')
  if (specs.techo_panoramico === true)     chips.push('Techo panorámico')
  if (specs.asientos_calefaccionados === true) chips.push('Asientos calefaccionados')
  if (specs.asientos_electricos === true)  chips.push('Asientos eléctricos')
  if (specs.control_crucero === true)      chips.push('Control crucero')
  if (specs.crucero_adaptativo === true)   chips.push('Crucero adaptativo')
  if (specs.camara_retroceso === true)     chips.push('Cámara de retroceso')
  if (specs.abs === true)                  chips.push('ABS')
  if (specs.esp === true)                  chips.push('ESP')
  if (specs.frenado_autonomo === true)     chips.push('Frenado autónomo')
  if (specs.hud === true)                  chips.push('HUD')
  if (specs.llantas_aleacion === true)     chips.push('Llantas de aleación')
  if (specs.alarma === true)               chips.push('Alarma')
  if (specs.arranque_sin_llave === true)   chips.push('Keyless entry')
  if (specs.gps_integrado === true)        chips.push('GPS integrado')
  if (specs.bluetooth === true)            chips.push('Bluetooth')
  if (specs.airbags)                       chips.push(`${specs.airbags} airbags`)
  if (specs.pantalla_pulg)                 chips.push(`Pantalla ${specs.pantalla_pulg}"`)
  if (specs.climatizacion === 'automatico') chips.push('Clima automático')
  if (specs.climatizacion === 'bizona')    chips.push('Clima bizona')
  if (specs.faros === 'full_led')          chips.push('Full LED')
  if (specs.tapizado === 'cuero')          chips.push('Tapizado cuero')
  if (specs.tapizado === 'alcantara')      chips.push('Tapizado Alcántara')
  return chips
}

function generarMsgWhatsApp(v, chips, tc) {
  const precioARS = v.precio_base ? `$${((v.precio_base) * (tc || 1415)).toLocaleString('es-AR')}` : 'Consultar precio'
  const equipTop = chips.slice(0, 5).join(' · ')
  return `🚗 *${v.marca} ${v.modelo} ${v.anio}*\n` +
    (v.version ? `_${v.version}_\n` : '') +
    `\n✅ ${Number(v.km_hs || 0).toLocaleString('es-AR')} km\n` +
    `🎨 Color ${v.color || 'a confirmar'}\n` +
    `⚙️ ${[v.transmision, v.combustible].filter(Boolean).join(' · ')}` + '\n' +
    (equipTop ? `\n✨ ${equipTop}\n` : '') +
    `\n💵 USD ${v.precio_base?.toLocaleString('es-AR') || '—'} / ${precioARS}\n` +
    `\n📲 ¿Querés coordinar una prueba de manejo?`
}

const TIPO_META = {
  ingreso:          { icono: '🚗', color: 'var(--c-accent)' },
  estado_cambio:    { icono: '🔄', color: 'var(--c-fg-2)' },
  foto_agregada:    { icono: '📸', color: '#8B5CF6' },
  doc_subido:       { icono: '📄', color: '#0EA5E9' },
  venta:            { icono: '🎉', color: '#10B981' },
  seña:             { icono: '💰', color: '#F59E0B' },
  lead:             { icono: '👤', color: '#6366F1' },
  prueba_manejo:    { icono: '🔑', color: '#F97316' },
  publicado:        { icono: '📢', color: '#22C55E' },
  precio_cambio:    { icono: '💲', color: '#EF4444' },
  ubicacion_cambio: { icono: '📍', color: '#84CC16' },
  gasto:            { icono: '🔧', color: '#94A3B8' },
  nota:             { icono: '📝', color: 'var(--c-fg-3)' },
}

function fmtFecha(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  const pad = n => String(n).padStart(2, '0')
  return `${pad(d.getDate())}/${pad(d.getMonth()+1)}/${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

const TIPOS_GASTO = {
  mecanica:      'Mecánica / Motor',
  chapa_pintura: 'Chapa y Pintura',
  detailing:     'Detailing / Limpieza',
  documentacion: 'Documentación',
  neumaticos:    'Neumáticos',
  electrica:     'Eléctrica',
  gnc:           'GNC',
  otro:          'Otro',
}

const EMPTY_GASTO = { tipo: 'mecanica', descripcion: '', monto: '', moneda: 'ARS', proveedor: '', fecha_gasto: new Date().toISOString().split('T')[0] }
const EMPTY_RESERVA = { cliente_nombre: '', cliente_telefono: '', monto_senia: '', moneda: 'USD', fecha_vencimiento: '', notas: '' }

// ── Galería con miniaturas ────────────────────────────────────
function Galeria({ fotos }) {
  const [idx, setIdx] = useState(0)
  const [lightbox, setLightbox] = useState(false)
  const total = fotos.length

  useEffect(() => {
    if (!lightbox) return
    function onKey(e) {
      if (e.key === 'ArrowLeft')  setIdx(i => (i - 1 + total) % total)
      if (e.key === 'ArrowRight') setIdx(i => (i + 1) % total)
      if (e.key === 'Escape')     setLightbox(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [lightbox, total])

  return (
    <div style={{ marginBottom: 20 }}>
      {lightbox && (
        <div
          onClick={() => setLightbox(false)}
          style={{
            position: 'fixed', inset: 0, zIndex: 9999,
            background: 'rgba(0,0,0,.92)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            cursor: 'zoom-out',
          }}
        >
          <button onClick={e => { e.stopPropagation(); setIdx(i => (i - 1 + total) % total) }}
            style={{
              position: 'absolute', left: 24, top: '50%', transform: 'translateY(-50%)',
              background: 'rgba(255,255,255,.1)', border: 'none', borderRadius: '50%',
              width: 48, height: 48, fontSize: 24, color: '#fff', cursor: 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>‹</button>
          <img src={fotos[idx].url} alt=""
            style={{ maxWidth: '90vw', maxHeight: '90vh', objectFit: 'contain' }}
            onClick={e => e.stopPropagation()} />
          <button onClick={e => { e.stopPropagation(); setIdx(i => (i + 1) % total) }}
            style={{
              position: 'absolute', right: 24, top: '50%', transform: 'translateY(-50%)',
              background: 'rgba(255,255,255,.1)', border: 'none', borderRadius: '50%',
              width: 48, height: 48, fontSize: 24, color: '#fff', cursor: 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>›</button>
          <div style={{ position: 'absolute', bottom: 24, left: '50%', transform: 'translateX(-50%)', color: '#fff', fontSize: 13 }}>
            {idx + 1} / {total}
          </div>
          <button onClick={() => setLightbox(false)}
            style={{
              position: 'absolute', top: 16, right: 16,
              background: 'rgba(255,255,255,.1)', border: 'none', borderRadius: '50%',
              width: 40, height: 40, fontSize: 20, color: '#fff', cursor: 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>✕</button>
        </div>
      )}
      <div style={{ position: 'relative', aspectRatio: '16/9', borderRadius: 'var(--r-lg)', overflow: 'hidden', background: 'var(--c-card)', marginBottom: 8 }}>
        {fotos[idx] ? (
          <img src={fotos[idx].url} alt=""
            style={{ width: '100%', height: '100%', objectFit: 'cover', cursor: 'zoom-in' }}
            onClick={() => setLightbox(true)} />
        ) : (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--c-fg-3)' }}>
            Sin fotos
          </div>
        )}
        {total > 1 && (
          <>
            <button onClick={() => setIdx(i => (i - 1 + total) % total)} style={{
              position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)',
              background: 'rgba(0,0,0,.6)', border: 'none', borderRadius: '50%',
              width: 36, height: 36, cursor: 'pointer', color: '#fff', fontSize: 18,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>&#8249;</button>
            <button onClick={() => setIdx(i => (i + 1) % total)} style={{
              position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)',
              background: 'rgba(0,0,0,.6)', border: 'none', borderRadius: '50%',
              width: 36, height: 36, cursor: 'pointer', color: '#fff', fontSize: 18,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>&#8250;</button>
          </>
        )}
        {total > 0 && (
          <div style={{
            position: 'absolute', bottom: 12, right: 12,
            background: 'rgba(0,0,0,.7)', borderRadius: 6,
            padding: '4px 10px', fontSize: 12, color: '#fff',
          }}>
            {idx + 1} / {total}
          </div>
        )}
      </div>
      {total > 1 && (
        <div style={{ display: 'flex', gap: 6, overflowX: 'auto', paddingBottom: 4 }}>
          {fotos.map((f, i) => (
            <button key={f.id || i} onClick={() => setIdx(i)} style={{
              flexShrink: 0, width: 64, height: 48, borderRadius: 6, overflow: 'hidden',
              border: i === idx ? '2px solid var(--c-accent)' : '2px solid transparent',
              cursor: 'pointer', padding: 0, background: 'var(--c-card)',
            }}>
              <img src={f.url} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Card Precio (panel derecho) ───────────────────────────────
function CardPrecio({ v, tc, onVenta, onSena, user, vendedores, onNegociacionChange }) {
  const precioARS = v.precio_base ? (v.precio_base * tc).toLocaleString('es-AR') : '—'
  const rol = user?.rol || 'externo'
  const puedeNegociar = rol === 'vendedor' || rol === 'dueno'

  const nombreNegociador = v.negociacion_vendedor_id
    ? (vendedores || []).find(vend => vend.id === v.negociacion_vendedor_id)?.nombre || 'otro vendedor'
    : null

  async function handleIniciar() {
    if (!user?.id) return
    try {
      await iniciarNegociacion(v.id, user.id)
      onNegociacionChange?.()
    } catch (e) { console.error(e) }
  }

  async function handleLiberar() {
    try {
      await liberarNegociacion(v.id)
      onNegociacionChange?.()
    } catch (e) { console.error(e) }
  }

  return (
    <div className="card" style={{ padding: 16 }}>
      <div style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--c-fg-3)', marginBottom: 8 }}>
        Precio
      </div>
      <div style={{ fontSize: 32, fontWeight: 700, marginBottom: 4 }}>
        USD {v.precio_base?.toLocaleString('es-AR') || '—'}
      </div>
      <div style={{ fontSize: 12, color: 'var(--c-fg-3)', marginBottom: 16 }}>
        ≈ ARS {precioARS} · TC ${tc?.toLocaleString?.() || '—'}
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        <button className="btn primary" style={{ width: '100%' }} onClick={onVenta}>
          Registrar venta
        </button>
        <button className="btn secondary" style={{ width: '100%' }} onClick={onSena}>
          Marcar como señado
        </button>

        {puedeNegociar && (
          <>
            {!v.en_negociacion ? (
              <button className="btn ghost" style={{ width: '100%', fontSize: 13 }} onClick={handleIniciar}>
                ⚡ Iniciar negociación
              </button>
            ) : v.negociacion_vendedor_id === user?.id ? (
              <button className="btn ghost" style={{ width: '100%', fontSize: 13, color: '#F5A623' }} onClick={handleLiberar}>
                🔓 Liberar negociación
              </button>
            ) : (
              <div style={{ fontSize: 12, color: '#F5A623', textAlign: 'center', padding: '6px 0' }}>
                ⚡ En negociación por {nombreNegociador}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

// ── Card Especificaciones (panel derecho) ─────────────────────
function CardSpecs({ v }) {
  const specs = v.specs || {}
  const items = [
    { label: 'Año', value: v.anio },
    { label: 'Km', value: v.km_hs ? `${Number(v.km_hs).toLocaleString('es-AR')} km` : '—' },
    { label: 'Motor', value: specs.potencia_hp ? `${specs.cilindrada || ''}cc · ${specs.potencia_hp} HP` : (v.motor_cv || v.combustible || '—') },
    { label: 'Transmisión', value: v.transmision || '—' },
    { label: 'Combustible', value: v.combustible || '—' },
    { label: 'Color', value: v.color || '—' },
    { label: 'Patente', value: v.patente || '—' },
    { label: 'Titular', value: v.specs?.titular || '1°' },
  ]
  return (
    <div className="card" style={{ padding: 16 }}>
      <div style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--c-fg-3)', marginBottom: 12 }}>
        Especificaciones
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px 12px' }}>
        {items.map(({ label, value }) => (
          <div key={label}>
            <div style={{ fontSize: 10, color: 'var(--c-fg-3)', textTransform: 'uppercase', marginBottom: 2 }}>{label}</div>
            <div style={{ fontSize: 13, fontWeight: 500 }}>{value || '—'}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function Detalle({ onLogout }) {
  const { id }   = useParams()
  const navigate = useNavigate()
  const TC       = useTc()
  const user     = useUser()

  const [data, setData]     = useState(null)
  const [tab, setTab]       = useState('info')
  const [foto, setFoto]     = useState(0)

  const [editing, setEditing]   = useState(false)
  const [editForm, setEditForm] = useState({})
  const [saving, setSaving]     = useState(false)

  const [aiModal, setAiModal]     = useState(null)
  const [aiResult, setAiResult]   = useState('')
  const [aiLoading, setAiLoading] = useState(false)
  const [tasacion, setTasacion]   = useState(null)
  const [tasLoading, setTasLoading] = useState(false)

  const [gastos, setGastos]             = useState([])
  const [gastoForm, setGastoForm]       = useState(EMPTY_GASTO)
  const [savingGasto, setSavingGasto]   = useState(false)
  const [showGastoForm, setShowGastoForm] = useState(false)

  const [reservas, setReservas]               = useState([])
  const [reservaForm, setReservaForm]         = useState(EMPTY_RESERVA)
  const [savingReserva, setSavingReserva]     = useState(false)
  const [showReservaForm, setShowReservaForm] = useState(false)

  const [docs, setDocs]         = useState(null)
  const [docsForm, setDocsForm] = useState({})
  const [savingDocs, setSavingDocs] = useState(false)
  const [docsSaved, setDocsSaved]   = useState(false)

  const [historial, setHistorial]           = useState([])
  const [histLoading, setHistLoading]       = useState(false)
  const [histNotaText, setHistNotaText]     = useState('')
  const [savingNota, setSavingNota]         = useState(false)

  const [ubicacionEdit, setUbicacionEdit] = useState(false)
  const [ubicacionVal,  setUbicacionVal]  = useState('')
  const [savingUbicacion, setSavingUbicacion] = useState(false)

  const [pubDesc, setPubDesc]         = useState('')
  const [pubDescLoading, setPubDescLoading] = useState(false)
  const [pubDescSaved, setPubDescSaved]     = useState(false)
  const [pubDescSaving, setPubDescSaving]   = useState(false)
  const [pubWspCopied, setPubWspCopied]     = useState(false)
  const [pubChipsCopied, setPubChipsCopied] = useState(false)

  // panel derecho: modal de reserva desde botón señado
  const [showSideReservaModal, setShowSideReservaModal] = useState(false)

  const [vendedores, setVendedores] = useState([])

  function reloadVehiculo() {
    getVehiculo(id).then(setData)
  }

  useEffect(() => {
    Promise.all([
      getVehiculo(id),
      getGastosByVehiculo(id),
      getReservasByVehiculo(id),
      getDocumentacion(id),
      getVendedores(),
    ]).then(([d, g, r, doc, vends]) => {
      setData(d); setGastos(g); setReservas(r); setVendedores(vends || [])
      const docData = doc || {}
      setDocs(docData)
      setDocsForm(docData)
    })
  }, [id])

  useEffect(() => {
    if (tab !== 'historial') return
    setHistLoading(true)
    getHistorialVehiculo(id)
      .then(setHistorial)
      .catch(console.error)
      .finally(() => setHistLoading(false))
  }, [id, tab])

  async function submitNota() {
    if (!histNotaText.trim()) return
    setSavingNota(true)
    try {
      await addHistorialEntry(id, 'nota', histNotaText.trim())
      setHistNotaText('')
      const h = await getHistorialVehiculo(id)
      setHistorial(h)
    } catch (e) { console.error(e) }
    finally { setSavingNota(false) }
  }

  async function saveDocs() {
    setSavingDocs(true); setDocsSaved(false)
    try {
      await upsertDocumentacion(id, docsForm)
      setDocsSaved(true)
      setTimeout(() => setDocsSaved(false), 3000)
    } catch (e) {
      console.error(e)
    } finally { setSavingDocs(false) }
  }
  const df = (k) => (e) => setDocsForm(p => ({ ...p, [k]: e.target.value }))
  const dc = (k) => (e) => setDocsForm(p => ({ ...p, [k]: e.target.checked }))

  if (!data) return (
    <div>
      <TopBar onLogout={onLogout} />
      <div className="main"><p style={{ color: 'var(--c-fg-2)' }}>Cargando…</p></div>
    </div>
  )

  const { vehiculo: v, medias } = data

  if (!v) return (
    <div>
      <TopBar onLogout={onLogout} />
      <div className="main">
        <div className="banner warning"><Icon name="alert" size={16} />Vehículo no encontrado.</div>
      </div>
    </div>
  )

  const fotos = medias.filter(m => m.tipo === 'foto' && m.url)

  const gastosTotalARS  = gastos.filter(g => g.moneda === 'ARS').reduce((s, g) => s + Number(g.monto || 0), 0)
  const gastosTotalUSD  = gastos.filter(g => g.moneda === 'USD').reduce((s, g) => s + Number(g.monto || 0), 0)
  const gastosEquivUSD  = gastosTotalUSD + (TC > 0 ? gastosTotalARS / TC : 0)
  const margenBruto     = v.precio_base && v.costo_compra ? v.precio_base - v.costo_compra - gastosEquivUSD : null

  const specs = [
    ['Combustible', v.combustible],
    ['Transmisión', v.transmision],
    ['Motor / CV', v.motor_cv],
    ['Tracción', v.traccion],
    ['Puertas', v.puertas],
    ...(v.specs ? Object.entries(v.specs) : []),
  ].filter(([, val]) => val)

  const chips = generateChipsFromSpecs(v.specs || {})

  function openEdit() {
    setEditForm({
      marca: v.marca, modelo: v.modelo, anio: v.anio,
      version: v.version || '', color: v.color || '',
      km_hs: v.km_hs || '', precio_base: v.precio_base || '',
      costo_compra: v.costo_compra || '', estado: v.estado,
      combustible: v.combustible || '', transmision: v.transmision || '',
      patente: v.patente || '', notas_internas: v.notas_internas || '',
      link_ml: v.link_ml || '', link_drive: v.link_drive || '',
      ubicacion: v.ubicacion || 'showroom',
      estado_recon: v.estado_recon || 'ingresado',
    })
    setEditing(true)
  }

  const fe = (k) => (e) => setEditForm(p => ({ ...p, [k]: e.target.value }))

  async function saveEdit() {
    setSaving(true)
    try {
      await updateVehiculo(v.id, {
        ...editForm,
        anio: Number(editForm.anio),
        km_hs: editForm.km_hs ? Number(editForm.km_hs) : null,
        precio_base: editForm.precio_base ? Number(editForm.precio_base) : null,
        costo_compra: editForm.costo_compra ? Number(editForm.costo_compra) : null,
      })
      setEditing(false)
      getVehiculo(id).then(setData)
    } finally { setSaving(false) }
  }

  async function runAI(tipo) {
    setAiModal(tipo); setAiResult(''); setAiLoading(true)
    try {
      if (tipo === 'descripcion') {
        const d = await callAI('/ai/descripcion-ml', { vehiculo: v, specs: v.specs || {} })
        setAiResult(d.texto)
      } else if (tipo === 'wsp') {
        const d = await callAI('/ai/mensaje-wsp', { vehiculo: v, specs: v.specs || {}, precio_usd: v.precio_base || 0, tipo_cambio: TC })
        setAiResult(d.texto)
      } else if (tipo === 'fotos') {
        const blobs = await Promise.all(fotos.slice(0, 3).map(f => fetch(f.url).then(r => r.blob())))
        const fileObjs = blobs.map((b, i) => new File([b], `foto${i}.jpg`, { type: b.type || 'image/jpeg' }))
        const d = await callAIFiles('/ai/analizar-fotos', fileObjs)
        setAiResult(d.texto)
      }
    } catch (e) { setAiResult('Error: ' + e.message) }
    finally { setAiLoading(false) }
  }

  async function handleTasacion() {
    if (!v.marca || !v.modelo) return
    setTasLoading(true); setTasacion(null)
    try {
      const d = await callAI('/ai/tasacion', {
        marca: v.marca, modelo: v.modelo, anio: v.anio || 0,
        version: v.version || '', km: v.km_hs || 0, estado: 'bueno',
      })
      setTasacion(d)
    } catch (e) { console.error(e) }
    finally { setTasLoading(false) }
  }

  const fg = (k) => (e) => setGastoForm(p => ({ ...p, [k]: e.target.value }))

  async function submitGasto() {
    if (!gastoForm.monto || Number(gastoForm.monto) <= 0) return
    setSavingGasto(true)
    try {
      await createGasto({ ...gastoForm, vehiculo_id: Number(id), monto: Number(gastoForm.monto) })
      setGastos(await getGastosByVehiculo(id))
      setShowGastoForm(false)
      setGastoForm(EMPTY_GASTO)
    } finally { setSavingGasto(false) }
  }

  const fr = (k) => (e) => setReservaForm(p => ({ ...p, [k]: e.target.value }))

  async function submitReserva() {
    if (!reservaForm.cliente_nombre || !reservaForm.monto_senia) return
    setSavingReserva(true)
    try {
      await createReserva({ ...reservaForm, vehiculo_id: Number(id), monto_senia: Number(reservaForm.monto_senia) })
      await updateVehiculo(v.id, { estado: 'señado' })
      const [r, d] = await Promise.all([getReservasByVehiculo(id), getVehiculo(id)])
      setReservas(r); setData(d)
      setShowReservaForm(false)
      setShowSideReservaModal(false)
      setReservaForm(EMPTY_RESERVA)
    } finally { setSavingReserva(false) }
  }

  async function openUbicacionEdit() {
    setUbicacionVal(v.ubicacion || 'showroom')
    setUbicacionEdit(true)
  }

  async function saveUbicacion() {
    setSavingUbicacion(true)
    try {
      await updateVehiculo(v.id, { ubicacion: ubicacionVal })
      setUbicacionEdit(false)
      getVehiculo(id).then(setData)
    } finally { setSavingUbicacion(false) }
  }

  // ── Render ────────────────────────────────────────────────────
  return (
    <div>
      <TopBar onLogout={onLogout} />
      <div className="main">
        <a className="back-link" onClick={() => navigate('/catalogo')}>
          <Icon name="arrow-l" size={14} /> Volver al catálogo
        </a>

        <div className="page-head">
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <h1 className="page-title">{v.marca} {v.modelo} {v.anio}</h1>
              {v.en_negociacion && (
                <span style={{
                  background: 'rgba(245,166,35,0.15)', color: '#F5A623',
                  border: '1px solid rgba(245,166,35,0.3)',
                  borderRadius: 20, padding: '3px 10px', fontSize: 12, fontWeight: 600,
                }}>
                  ⚡ En negociación
                </span>
              )}
            </div>
            <p className="page-caption">
              {v.version && <>Versión: <strong style={{ color: 'var(--c-fg)' }}>{v.version}</strong> · </>}
              Stock <strong style={{ color: 'var(--c-fg)', fontFamily: 'var(--mono)' }}>#{v.id}</strong>
              {v.patente && <> · Patente <strong style={{ color: 'var(--c-fg)', fontFamily: 'var(--mono)' }}>{v.patente}</strong></>}
            </p>
          </div>
          <div style={{ flex: 1 }} />
          {aiConfigured() && <>
            <button className="btn secondary" onClick={() => runAI('descripcion')}><Icon name="doc" size={14} />Desc. ML</button>
            <button className="btn secondary" onClick={() => runAI('wsp')}><Icon name="share" size={14} />Msg WSP</button>
            <button className="btn secondary" disabled={tasLoading} onClick={handleTasacion}>
              <Icon name="tag" size={14} />{tasLoading ? 'Tasando…' : 'Tasación'}
            </button>
          </>}
          <button className="btn secondary" onClick={() => navigate(`/agenda?vehiculo_id=${v.id}`)}>
            <Icon name="cal" size={14} />Prueba de manejo
          </button>
          <button className="btn primary" onClick={openEdit}><Icon name="edit" size={14} />Editar</button>
        </div>

        <div className="detail-head">
          <div className="dm">
            <div className="lbl">Estado</div>
            <div className="val" style={{ fontSize: 16 }}><StateBadge estado={v.estado} /></div>
          </div>
          <div className="dm">
            <div className="lbl">Ubicación</div>
            <div className="val" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              {ubicacionEdit ? (
                <>
                  <select
                    className="input"
                    style={{ fontSize: 12, padding: '2px 6px', height: 'auto' }}
                    value={ubicacionVal}
                    onChange={e => setUbicacionVal(e.target.value)}
                  >
                    {Object.entries(UBICACION_META).map(([val, m]) => (
                      <option key={val} value={val}>{m.label}</option>
                    ))}
                  </select>
                  <button className="btn primary" style={{ fontSize: 11, padding: '3px 8px' }}
                    disabled={savingUbicacion} onClick={saveUbicacion}>
                    {savingUbicacion ? '…' : 'Guardar'}
                  </button>
                  <button className="btn ghost" style={{ fontSize: 11, padding: '3px 6px' }}
                    onClick={() => setUbicacionEdit(false)}>
                    <Icon name="x" size={12} />
                  </button>
                </>
              ) : (
                <>
                  <StateBadge ubicacion={v.ubicacion || 'showroom'} />
                  <button className="btn ghost" style={{ padding: '2px 5px' }}
                    onClick={openUbicacionEdit} title="Cambiar ubicación">
                    <Icon name="edit" size={12} />
                  </button>
                </>
              )}
            </div>
          </div>
          <div className="dm">
            <div className="lbl">Reacond.</div>
            <div className="val"><StateBadge recon={v.estado_recon || 'ingresado'} /></div>
          </div>
          <div className="dm">
            <div className="lbl">Kilometraje</div>
            <div className="val">
              {v.km_hs?.toLocaleString('es-AR') || '0'}
              <span style={{ fontSize: 13, color: 'var(--c-fg-2)', fontWeight: 400, marginLeft: 4 }}>km</span>
            </div>
          </div>
          <div className="dm">
            <div className="lbl">Precio</div>
            <div className="val">
              <span style={{ fontSize: 14, color: 'var(--c-fg-2)', fontWeight: 500, marginRight: 4 }}>USD</span>
              {v.precio_base?.toLocaleString('es-AR')}
            </div>
          </div>
          <div className="dm">
            <div className="lbl">ARS</div>
            <div className="val g" style={{ fontSize: 16 }}>
              $ {((v.precio_base || 0) * TC).toLocaleString('es-AR')}
            </div>
          </div>
        </div>

        {/* Panel tasación */}
        {tasacion && (
          <div className="card" style={{ marginBottom: 16, borderLeft: '3px solid #22c55e' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#22c55e' }}>Tasación de mercado — IA</div>
              <button className="btn ghost" style={{ padding: '2px 6px' }} onClick={() => setTasacion(null)}><Icon name="x" size={14} /></button>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10, marginBottom: 10 }}>
              {[['Mínimo', tasacion.precio_min], ['Sugerido', tasacion.precio_sugerido], ['Máximo', tasacion.precio_max]].map(([label, val]) => (
                <div key={label} style={{ background: 'var(--c-bg-2)', borderRadius: 'var(--r)', padding: '8px 12px', textAlign: 'center' }}>
                  <div style={{ fontSize: 11, color: 'var(--c-fg-3)' }}>{label}</div>
                  <div style={{ fontSize: 15, fontWeight: 700 }}>USD {val?.toLocaleString('es-AR')}</div>
                </div>
              ))}
            </div>
            {tasacion.argautos_precio_usd && (
              <div style={{ fontSize: 12, color: 'var(--c-fg-2)', marginBottom: 6 }}>
                ArgAutos: USD {tasacion.argautos_precio_usd?.toLocaleString('es-AR')} · confianza: {tasacion.confianza}
              </div>
            )}
            {tasacion.razonamiento && <div style={{ fontSize: 12, color: 'var(--c-fg-2)' }}>{tasacion.razonamiento}</div>}
          </div>
        )}

        <div className="tabs">
          {[
            ['info', 'info', 'Información'],
            ['fotos', 'image', fotos.length > 0 ? `Fotos (${fotos.length})` : 'Fotos'],
            ['gastos', 'cash', gastos.length > 0 ? `Gastos (${gastos.length})` : 'Gastos'],
            ['res', 'users', reservas.length > 0 ? `Reservas (${reservas.length})` : 'Reservas'],
            ['docs', 'doc', 'Documentación'],
            ['pub', 'share', '🤖 Publicar'],
            ['historial', 'clock', 'Historial'],
          ].map(([k, ic, l]) => (
            <button key={k} className={tab === k ? 'on' : ''} onClick={() => setTab(k)}>
              {k !== 'pub' && <Icon name={ic} size={13} />}{l}
            </button>
          ))}
        </div>

        {/* ── LAYOUT 2 COLUMNAS — tabs info y fotos ── */}
        {(tab === 'info' || tab === 'fotos') && (
          <div style={{ display: 'flex', gap: 24, alignItems: 'flex-start' }}>

            {/* Columna principal */}
            <div style={{ flex: 1, minWidth: 0 }}>

              {/* ── TAB: INFO ── */}
              {tab === 'info' && (
                <div>
                  {/* Galería en tab info */}
                  {fotos.length > 0 && <Galeria fotos={fotos} />}

                  <div className="info-grid">
                    <div className="card info-card">
                      <h3><Icon name="cog" size={14} />Especificaciones</h3>
                      {specs.length > 0
                        ? specs.map(([k, val]) => <div key={k} className="kv"><span>{k}</span><span>{val}</span></div>)
                        : <p style={{ color: 'var(--c-fg-3)', fontSize: 13 }}>Sin datos cargados.</p>
                      }
                    </div>
                    <div className="card info-card">
                      <h3><Icon name="clipboard" size={14} />Identificación</h3>
                      <div className="kv"><span>Color</span><span>{v.color || '—'}</span></div>
                      <div className="kv"><span>Patente</span><span style={{ fontFamily: 'var(--mono)' }}>{v.patente || '—'}</span></div>
                      <div className="kv"><span>Tipo</span><span style={{ textTransform: 'capitalize' }}>{v.tipo}</span></div>
                      {v.vin && <div className="kv"><span>VIN</span><span style={{ fontFamily: 'var(--mono)', fontSize: 11 }}>{v.vin}</span></div>}
                      {v.link_ml && <div className="kv"><span>MercadoLibre</span><a href={v.link_ml} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--c-accent)', fontSize: 12 }}>Ver publicación</a></div>}
                      {v.link_drive && <div className="kv"><span>Drive</span><a href={v.link_drive} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--c-accent)', fontSize: 12 }}>Carpeta</a></div>}
                    </div>
                    <div className="card info-card">
                      <h3><Icon name="tag" size={14} />Precio</h3>
                      <div className="kv"><span>Precio base</span><span>USD {v.precio_base?.toLocaleString('es-AR') || '—'}</span></div>
                      <div className="kv"><span>En ARS</span><span>$ {((v.precio_base || 0) * TC).toLocaleString('es-AR')}</span></div>
                      {v.costo_compra > 0 && <div className="kv"><span>Costo compra</span><span>USD {v.costo_compra?.toLocaleString('es-AR')}</span></div>}
                      {margenBruto !== null && (
                        <div className="kv">
                          <span>Margen neto</span>
                          <span style={{ color: margenBruto >= 0 ? 'var(--c-success)' : 'var(--c-danger)', fontWeight: 600 }}>
                            USD {margenBruto.toLocaleString('es-AR', { maximumFractionDigits: 0 })}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Chips de equipamiento */}
                  {chips.length > 0 && (
                    <div style={{ marginTop: 16 }}>
                      <div style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase', color: 'var(--c-fg-3)', marginBottom: 8 }}>
                        Equipamiento destacado
                      </div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                        {chips.map(chip => (
                          <span key={chip} style={{
                            background: 'var(--c-card-2)', border: '1px solid var(--c-border)',
                            borderRadius: 20, padding: '4px 12px', fontSize: 12, color: 'var(--c-fg-2)',
                          }}>
                            {chip}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Notas internas */}
                  {v.notas_internas && (
                    <div className="card" style={{ marginTop: 16, padding: 16 }}>
                      <div style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase', color: 'var(--c-fg-3)', marginBottom: 8 }}>
                        Notas internas
                      </div>
                      <p style={{ fontSize: 13, color: 'var(--c-fg-2)', margin: 0, lineHeight: 1.6 }}>{v.notas_internas}</p>
                    </div>
                  )}
                </div>
              )}

              {/* ── TAB: FOTOS ── */}
              {tab === 'fotos' && (
                fotos.length === 0
                  ? <div className="banner info"><Icon name="info" size={16} />Sin fotos cargadas.</div>
                  : (
                    <>
                      {aiConfigured() && (
                        <div style={{ marginBottom: 12 }}>
                          <button className="btn secondary" onClick={() => runAI('fotos')}>
                            <Icon name="image" size={14} /> Analizar estado con IA
                          </button>
                        </div>
                      )}
                      <div style={{ aspectRatio: '16/9', background: 'var(--c-card-2)', borderRadius: 'var(--r-lg)', overflow: 'hidden', marginBottom: 12, position: 'relative' }}>
                        <img src={fotos[foto].url} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                        <span style={{ position: 'absolute', bottom: 12, right: 12, background: 'rgba(0,0,0,.6)', color: '#fff', fontSize: 12, padding: '3px 10px', borderRadius: 999 }}>
                          {foto + 1} / {fotos.length}
                        </span>
                        {foto > 0 && (
                          <button onClick={() => setFoto(f => f - 1)} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', background: 'rgba(0,0,0,.5)', border: 'none', borderRadius: '50%', width: 36, height: 36, cursor: 'pointer', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                            <Icon name="chev-l" size={18} />
                          </button>
                        )}
                        {foto < fotos.length - 1 && (
                          <button onClick={() => setFoto(f => f + 1)} style={{ position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)', background: 'rgba(0,0,0,.5)', border: 'none', borderRadius: '50%', width: 36, height: 36, cursor: 'pointer', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                            <Icon name="chev-r" size={18} />
                          </button>
                        )}
                      </div>
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(80px, 1fr))', gap: 6 }}>
                        {fotos.map((f, i) => (
                          <div key={i} onClick={() => setFoto(i)} style={{ aspectRatio: '4/3', borderRadius: 'var(--r-sm)', overflow: 'hidden', cursor: 'pointer', border: `2px solid ${i === foto ? 'var(--c-success)' : 'transparent'}` }}>
                            <img src={f.url} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                          </div>
                        ))}
                      </div>
                    </>
                  )
              )}
            </div>

            {/* Panel derecho fijo — 340px */}
            <div style={{ width: 340, flexShrink: 0, display: 'flex', flexDirection: 'column', gap: 16 }}>
              <CardPrecio
                v={v}
                tc={TC}
                onVenta={() => { setReservaForm(EMPTY_RESERVA); setShowSideReservaModal(true) }}
                onSena={() => { setReservaForm(EMPTY_RESERVA); setShowSideReservaModal(true) }}
                user={user}
                vendedores={vendedores}
                onNegociacionChange={reloadVehiculo}
              />
              <CardSpecs v={v} />
              {reservas.length > 0 && (
                <div className="card" style={{ padding: 16 }}>
                  <div style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--c-fg-3)', marginBottom: 12 }}>
                    Prospectos interesados
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {reservas.slice(0, 5).map(r => (
                      <div key={r.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div>
                          <div style={{ fontSize: 13, fontWeight: 500 }}>{r.cliente_nombre}</div>
                          {r.cliente_telefono && <div style={{ fontSize: 11, color: 'var(--c-fg-3)' }}>{r.cliente_telefono}</div>}
                        </div>
                        <span className={`badge ${r.estado === 'activa' || !r.estado ? 'success' : r.estado === 'vencida' ? 'danger' : 'neutral'}`} style={{ fontSize: 10 }}>
                          <span className="cdot" />{r.estado || 'activa'}
                        </span>
                      </div>
                    ))}
                    {reservas.length > 5 && (
                      <div style={{ fontSize: 12, color: 'var(--c-fg-3)', textAlign: 'center' }}>
                        +{reservas.length - 5} más
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ── TAB: GASTOS ── */}
        {tab === 'gastos' && (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <div style={{ display: 'flex', gap: 24 }}>
                {gastosTotalARS > 0 && (
                  <div>
                    <div style={{ fontSize: 11, color: 'var(--c-fg-2)', marginBottom: 2 }}>Total ARS</div>
                    <strong>$ {gastosTotalARS.toLocaleString('es-AR')}</strong>
                  </div>
                )}
                {gastosTotalUSD > 0 && (
                  <div>
                    <div style={{ fontSize: 11, color: 'var(--c-fg-2)', marginBottom: 2 }}>Total USD</div>
                    <strong>USD {gastosTotalUSD.toLocaleString('es-AR')}</strong>
                  </div>
                )}
                {gastos.length > 0 && (
                  <div>
                    <div style={{ fontSize: 11, color: 'var(--c-fg-2)', marginBottom: 2 }}>Equiv. USD</div>
                    <strong style={{ color: 'var(--c-accent)' }}>USD {gastosEquivUSD.toLocaleString('es-AR', { maximumFractionDigits: 0 })}</strong>
                  </div>
                )}
              </div>
              <button className="btn primary" onClick={() => setShowGastoForm(true)}>
                <Icon name="plus" size={14} /> Agregar gasto
              </button>
            </div>

            {gastos.length === 0
              ? <div className="banner info"><Icon name="info" size={16} />Sin gastos registrados para este vehículo.</div>
              : gastos.map(g => (
                <div key={g.id} className="list-row" style={{ cursor: 'default' }}>
                  <div>
                    <div className="v-title">{TIPOS_GASTO[g.tipo] || g.tipo}</div>
                    <div className="v-meta">{g.descripcion || '—'}{g.proveedor ? ` · ${g.proveedor}` : ''}</div>
                  </div>
                  <div style={{ color: 'var(--c-fg-2)', fontSize: 12 }}>{g.fecha_gasto}</div>
                  <div className="price-cell">
                    <strong>{g.moneda} {Number(g.monto || 0).toLocaleString('es-AR')}</strong>
                  </div>
                </div>
              ))
            }

            {showGastoForm && (
              <Modal title="Registrar gasto" onClose={() => setShowGastoForm(false)}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                  <FormField label="Tipo de gasto">
                    <select className="input" value={gastoForm.tipo} onChange={fg('tipo')}>
                      {Object.entries(TIPOS_GASTO).map(([k, lbl]) => <option key={k} value={k}>{lbl}</option>)}
                    </select>
                  </FormField>
                  <FormField label="Proveedor / Taller">
                    <input className="input" value={gastoForm.proveedor} onChange={fg('proveedor')} placeholder="Taller El Turco…" />
                  </FormField>
                  <FormField label="Descripción">
                    <input className="input" value={gastoForm.descripcion} onChange={fg('descripcion')} placeholder="Aceite + filtros, cubiertas…" />
                  </FormField>
                  <FormField label="Fecha">
                    <input className="input" type="date" value={gastoForm.fecha_gasto} onChange={fg('fecha_gasto')} />
                  </FormField>
                  <FormField label="Monto" required>
                    <input className="input" type="number" value={gastoForm.monto} onChange={fg('monto')} min={0} />
                  </FormField>
                  <FormField label="Moneda">
                    <select className="input" value={gastoForm.moneda} onChange={fg('moneda')}>
                      <option value="ARS">ARS</option>
                      <option value="USD">USD</option>
                    </select>
                  </FormField>
                </div>
                <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', marginTop: 16 }}>
                  <button className="btn secondary" onClick={() => setShowGastoForm(false)}>Cancelar</button>
                  <button className="btn primary" onClick={submitGasto} disabled={savingGasto || !gastoForm.monto}>
                    {savingGasto ? 'Guardando…' : <><Icon name="check" size={14} /> Guardar</>}
                  </button>
                </div>
              </Modal>
            )}
          </div>
        )}

        {/* ── TAB: RESERVAS ── */}
        {tab === 'res' && (
          <div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 16 }}>
              {v.estado === 'disponible' && (
                <button className="btn primary" onClick={() => setShowReservaForm(true)}>
                  <Icon name="plus" size={14} /> Registrar seña
                </button>
              )}
            </div>

            {reservas.length === 0
              ? <div className="banner info"><Icon name="info" size={16} />Sin reservas activas para este vehículo.</div>
              : reservas.map(r => (
                <div key={r.id} className="card" style={{ marginBottom: 10 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div>
                      <strong>{r.cliente_nombre}</strong>
                      {r.cliente_telefono && <div style={{ color: 'var(--c-fg-2)', fontSize: 12, marginTop: 2 }}>{r.cliente_telefono}</div>}
                      {r.notas && <div style={{ color: 'var(--c-fg-2)', fontSize: 12, marginTop: 4 }}>{r.notas}</div>}
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <div style={{ fontWeight: 600 }}>{r.moneda} {Number(r.monto_senia || 0).toLocaleString('es-AR')}</div>
                      {r.fecha_vencimiento && (
                        <div style={{ fontSize: 12, color: new Date(r.fecha_vencimiento) < new Date() ? 'var(--c-danger)' : 'var(--c-fg-2)', marginTop: 2 }}>
                          Vence: {r.fecha_vencimiento}
                        </div>
                      )}
                      <span className={`badge ${r.estado === 'activa' || !r.estado ? 'success' : r.estado === 'vencida' ? 'danger' : 'neutral'}`} style={{ marginTop: 4 }}>
                        <span className="cdot" />{r.estado || 'activa'}
                      </span>
                    </div>
                  </div>
                </div>
              ))
            }

            {showReservaForm && (
              <Modal title="Registrar seña" onClose={() => setShowReservaForm(false)}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                  <FormField label="Nombre cliente" required>
                    <input className="input" value={reservaForm.cliente_nombre} onChange={fr('cliente_nombre')} placeholder="Juan Pérez" />
                  </FormField>
                  <FormField label="Teléfono">
                    <input className="input" value={reservaForm.cliente_telefono} onChange={fr('cliente_telefono')} placeholder="+54 9 11…" />
                  </FormField>
                  <FormField label="Monto seña" required>
                    <input className="input" type="number" value={reservaForm.monto_senia} onChange={fr('monto_senia')} min={0} />
                  </FormField>
                  <FormField label="Moneda">
                    <select className="input" value={reservaForm.moneda} onChange={fr('moneda')}>
                      <option value="USD">USD</option>
                      <option value="ARS">ARS</option>
                    </select>
                  </FormField>
                  <FormField label="Fecha vencimiento" hint="Si no paga antes de esta fecha la seña caduca">
                    <input className="input" type="date" value={reservaForm.fecha_vencimiento} onChange={fr('fecha_vencimiento')} />
                  </FormField>
                  <FormField label="Notas">
                    <input className="input" value={reservaForm.notas} onChange={fr('notas')} />
                  </FormField>
                </div>
                <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', marginTop: 16 }}>
                  <button className="btn secondary" onClick={() => setShowReservaForm(false)}>Cancelar</button>
                  <button className="btn primary" onClick={submitReserva} disabled={savingReserva || !reservaForm.cliente_nombre || !reservaForm.monto_senia}>
                    {savingReserva ? 'Registrando…' : <><Icon name="check" size={14} /> Guardar seña</>}
                  </button>
                </div>
              </Modal>
            )}
          </div>
        )}

        {/* ── TAB: DOCS ── */}
        {tab === 'docs' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>

            {/* Verificación policial */}
            <div className="card" style={{ padding: 18 }}>
              <h4 style={{ margin: '0 0 14px', fontSize: 14 }}>🚔 Verificación policial</h4>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px,1fr))', gap: 12 }}>
                <label style={{ fontSize: 12, color: 'var(--c-fg-2)' }}>
                  Estado
                  <select className="input" style={{ marginTop: 4 }} value={docsForm.verificacion_estado || 'pendiente'} onChange={df('verificacion_estado')}>
                    {['pendiente','ok','con_observaciones','no_realizada'].map(o => <option key={o}>{o}</option>)}
                  </select>
                </label>
                <label style={{ fontSize: 12, color: 'var(--c-fg-2)' }}>
                  Fecha
                  <input className="input" type="date" style={{ marginTop: 4 }} value={docsForm.verificacion_fecha || ''} onChange={df('verificacion_fecha')} />
                </label>
                <label style={{ fontSize: 12, color: 'var(--c-fg-2)' }}>
                  Vencimiento
                  <input className="input" type="date" style={{ marginTop: 4 }} value={docsForm.verificacion_vencimiento || ''} onChange={df('verificacion_vencimiento')} />
                </label>
                <label style={{ fontSize: 12, color: 'var(--c-fg-2)', gridColumn: '1 / -1' }}>
                  Notas
                  <input className="input" style={{ marginTop: 4 }} value={docsForm.verificacion_notas || ''} onChange={df('verificacion_notas')} />
                </label>
              </div>
            </div>

            {/* VTV */}
            <div className="card" style={{ padding: 18 }}>
              <h4 style={{ margin: '0 0 14px', fontSize: 14 }}>🔧 VTV</h4>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px,1fr))', gap: 12 }}>
                <label style={{ fontSize: 12, color: 'var(--c-fg-2)' }}>
                  Estado
                  <select className="input" style={{ marginTop: 4 }} value={docsForm.vtv_estado || 'pendiente'} onChange={df('vtv_estado')}>
                    {['pendiente','al_dia','vencida'].map(o => <option key={o}>{o}</option>)}
                  </select>
                </label>
                <label style={{ fontSize: 12, color: 'var(--c-fg-2)' }}>
                  Vencimiento
                  <input className="input" type="date" style={{ marginTop: 4 }} value={docsForm.vtv_vencimiento || ''} onChange={df('vtv_vencimiento')} />
                </label>
                <label style={{ fontSize: 12, color: 'var(--c-fg-2)' }}>
                  Provincia
                  <input className="input" style={{ marginTop: 4 }} value={docsForm.vtv_provincia || ''} onChange={df('vtv_provincia')} />
                </label>
              </div>
            </div>

            {/* Informe de dominio */}
            <div className="card" style={{ padding: 18 }}>
              <h4 style={{ margin: '0 0 14px', fontSize: 14 }}>📜 Informe de dominio</h4>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px,1fr))', gap: 12 }}>
                <label style={{ fontSize: 12, color: 'var(--c-fg-2)' }}>
                  Estado
                  <select className="input" style={{ marginTop: 4 }} value={docsForm.dominio_estado || 'pendiente'} onChange={df('dominio_estado')}>
                    {['pendiente','sin_gravamen','con_prenda','inhibido','sin_consultar'].map(o => <option key={o}>{o}</option>)}
                  </select>
                </label>
                <label style={{ fontSize: 12, color: 'var(--c-fg-2)' }}>
                  ¿Con prenda?
                  <select className="input" style={{ marginTop: 4 }} value={docsForm.dominio_prenda ? 'si' : 'no'} onChange={e => setDocsForm(p => ({ ...p, dominio_prenda: e.target.value === 'si' }))}>
                    <option value="no">No</option><option value="si">Sí</option>
                  </select>
                </label>
                {docsForm.dominio_prenda && (
                  <label style={{ fontSize: 12, color: 'var(--c-fg-2)' }}>
                    Monto prenda
                    <input className="input" type="number" style={{ marginTop: 4 }} value={docsForm.dominio_monto_prenda || ''} onChange={df('dominio_monto_prenda')} />
                  </label>
                )}
                <label style={{ fontSize: 12, color: 'var(--c-fg-2)', gridColumn: '1 / -1' }}>
                  Notas
                  <input className="input" style={{ marginTop: 4 }} value={docsForm.dominio_notas || ''} onChange={df('dominio_notas')} />
                </label>
              </div>
            </div>

            {/* Documentos físicos */}
            <div className="card" style={{ padding: 18 }}>
              <h4 style={{ margin: '0 0 14px', fontSize: 14 }}>📁 Documentos físicos</h4>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px,1fr))', gap: 12 }}>
                <label style={{ fontSize: 12, color: 'var(--c-fg-2)' }}>
                  Título original
                  <select className="input" style={{ marginTop: 4 }} value={docsForm.titulo_original || 'pendiente'} onChange={df('titulo_original')}>
                    {['pendiente','en_poder','no_tiene','en_tramite'].map(o => <option key={o}>{o}</option>)}
                  </select>
                </label>
                <label style={{ fontSize: 12, color: 'var(--c-fg-2)', display: 'flex', flexDirection: 'column', gap: 6 }}>
                  <span>Cédula verde</span>
                  <label style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <input type="checkbox" checked={!!docsForm.cedula_verde} onChange={dc('cedula_verde')} />
                    <span>{docsForm.cedula_verde ? 'Presente' : 'Ausente'}</span>
                  </label>
                </label>
                <label style={{ fontSize: 12, color: 'var(--c-fg-2)', display: 'flex', flexDirection: 'column', gap: 6 }}>
                  <span>Cédula azul</span>
                  <label style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <input type="checkbox" checked={!!docsForm.cedula_azul} onChange={dc('cedula_azul')} />
                    <span>{docsForm.cedula_azul ? 'Presente' : 'Ausente'}</span>
                  </label>
                </label>
                <label style={{ fontSize: 12, color: 'var(--c-fg-2)', display: 'flex', flexDirection: 'column', gap: 6 }}>
                  <span>Formulario 08</span>
                  <label style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <input type="checkbox" checked={!!docsForm.form08} onChange={dc('form08')} />
                    <span>{docsForm.form08 ? 'Presente' : 'Ausente'}</span>
                  </label>
                </label>
              </div>
            </div>

            {/* Transferencia */}
            <div className="card" style={{ padding: 18 }}>
              <h4 style={{ margin: '0 0 14px', fontSize: 14 }}>📝 Transferencia</h4>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px,1fr))', gap: 12 }}>
                <label style={{ fontSize: 12, color: 'var(--c-fg-2)' }}>
                  Estado
                  <select className="input" style={{ marginTop: 4 }} value={docsForm.transferencia_estado || 'pendiente'} onChange={df('transferencia_estado')}>
                    {['pendiente','en_tramite','completada','no_aplica'].map(o => <option key={o}>{o}</option>)}
                  </select>
                </label>
                <label style={{ fontSize: 12, color: 'var(--c-fg-2)' }}>
                  Fecha límite
                  <input className="input" type="date" style={{ marginTop: 4 }} value={docsForm.transferencia_fecha_limite || ''} onChange={df('transferencia_fecha_limite')} />
                </label>
                <label style={{ fontSize: 12, color: 'var(--c-fg-2)' }}>
                  Gestoría
                  <input className="input" style={{ marginTop: 4 }} value={docsForm.transferencia_gestoria || ''} onChange={df('transferencia_gestoria')} />
                </label>
                <label style={{ fontSize: 12, color: 'var(--c-fg-2)', gridColumn: '1 / -1' }}>
                  Notas
                  <input className="input" style={{ marginTop: 4 }} value={docsForm.transferencia_notas || ''} onChange={df('transferencia_notas')} />
                </label>
              </div>
            </div>

            {/* Multas */}
            <div className="card" style={{ padding: 18 }}>
              <h4 style={{ margin: '0 0 14px', fontSize: 14 }}>⚠️ Multas</h4>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px,1fr))', gap: 12 }}>
                <label style={{ fontSize: 12, color: 'var(--c-fg-2)' }}>
                  Estado
                  <select className="input" style={{ marginTop: 4 }} value={docsForm.multas_estado || 'sin consultar'} onChange={df('multas_estado')}>
                    {['sin consultar','sin_multas','con_multas','pendiente_consulta'].map(o => <option key={o}>{o}</option>)}
                  </select>
                </label>
                <label style={{ fontSize: 12, color: 'var(--c-fg-2)', gridColumn: '1 / -1' }}>
                  Notas
                  <input className="input" style={{ marginTop: 4 }} value={docsForm.multas_notas || ''} onChange={df('multas_notas')} />
                </label>
              </div>
            </div>

            {/* Guardar */}
            <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
              <button className="btn primary" disabled={savingDocs} onClick={saveDocs}>
                {savingDocs ? 'Guardando…' : <><Icon name="check" size={14} /> Guardar documentación</>}
              </button>
              {docsSaved && <span style={{ color: 'var(--c-success)', fontSize: 13 }}>✓ Guardado</span>}
            </div>
          </div>
        )}

        {/* ── TAB: HISTORIAL ── */}
        {tab === 'historial' && (
          <div>
            {histLoading && <p style={{ color: 'var(--c-fg-2)', fontSize: 13 }}>Cargando historial…</p>}

            {!histLoading && historial.length === 0 && (
              <div className="banner info"><Icon name="info" size={16} />Sin eventos registrados aún.</div>
            )}

            {!histLoading && historial.length > 0 && (
              <div style={{ position: 'relative', paddingLeft: 32 }}>
                <div style={{
                  position: 'absolute', left: 10, top: 8, bottom: 8,
                  width: 2, background: 'var(--c-border)', borderRadius: 2,
                }} />

                {historial.map((ev, i) => {
                  const meta = TIPO_META[ev.tipo] || { icono: '•', color: 'var(--c-fg-3)' }
                  return (
                    <div key={ev.id} style={{ position: 'relative', marginBottom: i < historial.length - 1 ? 20 : 0 }}>
                      <div style={{
                        position: 'absolute', left: -27, top: 2,
                        width: 20, height: 20, borderRadius: '50%',
                        background: 'var(--c-bg)', border: `2px solid ${meta.color}`,
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        fontSize: 10, lineHeight: 1,
                      }}>
                        {meta.icono}
                      </div>

                      <div style={{
                        background: 'var(--c-card)', border: '1px solid var(--c-border)',
                        borderRadius: 'var(--r)', padding: '10px 14px',
                      }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }}>
                          <div style={{ flex: 1 }}>
                            <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--c-fg)' }}>
                              {ev.descripcion}
                            </span>
                            {ev.vendedor?.nombre && (
                              <div style={{ fontSize: 11, color: 'var(--c-fg-3)', marginTop: 3 }}>
                                por {ev.vendedor.nombre}
                              </div>
                            )}
                          </div>
                          <div style={{ fontSize: 11, color: 'var(--c-fg-3)', whiteSpace: 'nowrap', flexShrink: 0 }}>
                            {fmtFecha(ev.created_at)}
                          </div>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}

            {/* Agregar nota */}
            <div style={{
              marginTop: 24, background: 'var(--c-card)',
              border: '1px solid var(--c-border)', borderRadius: 'var(--r)', padding: 14,
            }}>
              <div style={{ fontSize: 12, color: 'var(--c-fg-2)', marginBottom: 8, fontWeight: 500 }}>
                📝 Agregar nota
              </div>
              <div style={{ display: 'flex', gap: 10 }}>
                <input
                  className="input"
                  style={{ flex: 1 }}
                  placeholder="Ej: Cliente llamó para consultar, revisión mecánica ok…"
                  value={histNotaText}
                  onChange={e => setHistNotaText(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && !savingNota && submitNota()}
                />
                <button
                  className="btn primary"
                  onClick={submitNota}
                  disabled={savingNota || !histNotaText.trim()}
                >
                  {savingNota ? '…' : <><Icon name="plus" size={14} /> Agregar</>}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ── TAB: PUBLICAR ── */}
        {tab === 'pub' && (() => {
          const pubChips = generateChipsFromSpecs(v.specs || {})
          return (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>

              {/* Descripción MercadoLibre */}
              <div className="card" style={{ padding: 18 }}>
                <h4 style={{ margin: '0 0 14px', fontSize: 14 }}>📝 Descripción para MercadoLibre</h4>
                <div style={{ display: 'flex', gap: 10, marginBottom: 12, flexWrap: 'wrap', alignItems: 'center' }}>
                  <button
                    className="btn secondary"
                    disabled={pubDescLoading}
                    onClick={async () => {
                      setPubDescLoading(true)
                      try {
                        const d = await callAI('/ai/descripcion-ml', { vehiculo: v, specs: v.specs || {} })
                        setPubDesc(d.texto || '')
                      } catch {
                        const equipTxt = pubChips.length > 0
                          ? `\n\n🔧 Equipamiento:\n${pubChips.map(c => '• ' + c).join('\n')}`
                          : ''
                        setPubDesc(
                          `🚗 ${v.marca} ${v.modelo} ${v.anio}${v.version ? ` — ${v.version}` : ''}\n\n` +
                          `✅ ${Number(v.km_hs || 0).toLocaleString('es-AR')} km\n` +
                          `🎨 Color: ${v.color || 'a confirmar'}\n` +
                          `⚙️ ${[v.transmision, v.combustible].filter(Boolean).join(' — ')}` +
                          equipTxt
                        )
                      } finally { setPubDescLoading(false) }
                    }}
                  >
                    {pubDescLoading ? '⏳ Generando…' : '✨ Generar con IA'}
                  </button>
                  {(pubDesc || v.descripcion_publica) && (
                    <>
                      <button
                        className="btn secondary"
                        onClick={() => navigator.clipboard.writeText(pubDesc || v.descripcion_publica || '')}
                      >
                        <Icon name="clipboard" size={14} /> Copiar
                      </button>
                      <button
                        className="btn primary"
                        disabled={pubDescSaving}
                        onClick={async () => {
                          setPubDescSaving(true)
                          try {
                            await updateVehiculo(v.id, { descripcion_publica: pubDesc || v.descripcion_publica })
                            setPubDescSaved(true)
                            setTimeout(() => setPubDescSaved(false), 3000)
                          } finally { setPubDescSaving(false) }
                        }}
                      >
                        {pubDescSaving ? 'Guardando…' : <><Icon name="check" size={14} /> Guardar</>}
                      </button>
                      {pubDescSaved && <span style={{ color: 'var(--c-success)', fontSize: 13 }}>✓ Guardado</span>}
                    </>
                  )}
                </div>
                {(pubDesc || v.descripcion_publica) ? (
                  <textarea
                    className="input"
                    rows={10}
                    value={pubDesc || v.descripcion_publica || ''}
                    onChange={e => setPubDesc(e.target.value)}
                    style={{ resize: 'vertical', fontSize: 13, fontFamily: 'inherit' }}
                  />
                ) : (
                  <p style={{ color: 'var(--c-fg-3)', fontSize: 13, margin: 0 }}>
                    Hacé clic en &ldquo;Generar con IA&rdquo; para crear una descripción lista para publicar.
                  </p>
                )}
              </div>

              {/* Chips de equipamiento */}
              <div className="card" style={{ padding: 18 }}>
                <h4 style={{ margin: '0 0 14px', fontSize: 14, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <span>🏷️ Equipamiento destacado</span>
                  {pubChips.length > 0 && (
                    <button
                      className="btn secondary"
                      style={{ fontSize: 12 }}
                      onClick={() => {
                        navigator.clipboard.writeText(pubChips.join(', '))
                        setPubChipsCopied(true)
                        setTimeout(() => setPubChipsCopied(false), 2000)
                      }}
                    >
                      <Icon name="clipboard" size={13} /> {pubChipsCopied ? '✓ Copiado' : 'Copiar todo'}
                    </button>
                  )}
                </h4>
                {pubChips.length > 0 ? (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                    {pubChips.map(chip => (
                      <span
                        key={chip}
                        title="Clic para copiar"
                        onClick={() => navigator.clipboard.writeText(chip)}
                        style={{
                          background: 'var(--c-bg-2)',
                          border: '1px solid var(--c-border)',
                          borderRadius: 999,
                          padding: '4px 12px',
                          fontSize: 12,
                          color: 'var(--c-fg)',
                          cursor: 'pointer',
                          userSelect: 'none',
                        }}
                      >
                        {chip}
                      </span>
                    ))}
                  </div>
                ) : (
                  <p style={{ color: 'var(--c-fg-3)', fontSize: 13, margin: 0 }}>
                    No hay equipamiento cargado en las specs. Editá el vehículo y completá las specs para ver los chips.
                  </p>
                )}
              </div>

              {/* Mensaje WhatsApp */}
              <div className="card" style={{ padding: 18 }}>
                <h4 style={{ margin: '0 0 14px', fontSize: 14 }}>💬 Mensaje WhatsApp</h4>
                <div style={{ marginBottom: 12 }}>
                  <button
                    className="btn secondary"
                    onClick={() => {
                      navigator.clipboard.writeText(generarMsgWhatsApp(v, pubChips, TC))
                      setPubWspCopied(true)
                      setTimeout(() => setPubWspCopied(false), 2500)
                    }}
                  >
                    {pubWspCopied ? '✓ ¡Copiado!' : '📋 Generar y copiar'}
                  </button>
                </div>
                <pre style={{
                  background: 'var(--c-bg-2)',
                  borderRadius: 'var(--r)',
                  padding: '12px 14px',
                  fontSize: 12,
                  color: 'var(--c-fg-2)',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                  margin: 0,
                  fontFamily: 'inherit',
                  lineHeight: 1.6,
                }}>
                  {generarMsgWhatsApp(v, pubChips, TC)}
                </pre>
              </div>

            </div>
          )
        })()}
      </div>

      {/* ── AI Modal ── */}
      {aiModal && (
        <Modal
          title={aiModal === 'descripcion' ? 'Descripción MercadoLibre' : aiModal === 'wsp' ? 'Mensaje WhatsApp' : 'Análisis de fotos con IA'}
          onClose={() => { setAiModal(null); setAiResult('') }}
          wide
        >
          {aiLoading
            ? <p style={{ color: 'var(--c-fg-2)', padding: '24px 0', textAlign: 'center' }}>Generando con IA…</p>
            : (
              <>
                <textarea className="input" rows={12} readOnly value={aiResult}
                  style={{ resize: 'vertical', fontFamily: aiModal === 'wsp' ? 'inherit' : 'var(--mono)', fontSize: 13 }}
                />
                <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', marginTop: 12 }}>
                  <button className="btn secondary" onClick={() => navigator.clipboard.writeText(aiResult)}>
                    <Icon name="clipboard" size={14} /> Copiar
                  </button>
                  <button className="btn primary" onClick={() => { setAiModal(null); setAiResult('') }}>Cerrar</button>
                </div>
              </>
            )
          }
        </Modal>
      )}

      {/* ── Edit Modal ── */}
      {editing && (
        <Modal title="Editar vehículo" onClose={() => setEditing(false)} wide>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
            <FormField label="Marca"><input className="input" value={editForm.marca} onChange={fe('marca')} /></FormField>
            <FormField label="Modelo"><input className="input" value={editForm.modelo} onChange={fe('modelo')} /></FormField>
            <FormField label="Año"><input className="input" type="number" value={editForm.anio} onChange={fe('anio')} /></FormField>
            <FormField label="Versión"><input className="input" value={editForm.version} onChange={fe('version')} /></FormField>
            <FormField label="Patente"><input className="input" value={editForm.patente} onChange={fe('patente')} /></FormField>
            <FormField label="Color"><input className="input" value={editForm.color} onChange={fe('color')} /></FormField>
            <FormField label="Km / Hs"><input className="input" type="number" value={editForm.km_hs} onChange={fe('km_hs')} /></FormField>
            <FormField label="Precio USD"><input className="input" type="number" value={editForm.precio_base} onChange={fe('precio_base')} /></FormField>
            <FormField label="Costo USD"><input className="input" type="number" value={editForm.costo_compra} onChange={fe('costo_compra')} /></FormField>
            <FormField label="Estado">
              <select className="input" value={editForm.estado} onChange={fe('estado')}>
                {['disponible', 'señado', 'en_revision', 'en_preparacion', 'vendido'].map(e =>
                  <option key={e} value={e}>{e.replace(/_/g, ' ')}</option>
                )}
              </select>
            </FormField>
            <FormField label="Combustible"><input className="input" value={editForm.combustible} onChange={fe('combustible')} /></FormField>
            <FormField label="Transmisión"><input className="input" value={editForm.transmision} onChange={fe('transmision')} /></FormField>
            <FormField label="Link MercadoLibre">
              <input className="input" value={editForm.link_ml} onChange={fe('link_ml')} placeholder="https://auto.mercadolibre.com.ar/…" />
            </FormField>
            <FormField label="Link Drive">
              <input className="input" value={editForm.link_drive} onChange={fe('link_drive')} placeholder="https://drive.google.com/…" />
            </FormField>
            <FormField label="Ubicación">
              <select className="input" value={editForm.ubicacion} onChange={fe('ubicacion')}>
                {Object.entries(UBICACION_META).map(([val, m]) => (
                  <option key={val} value={val}>{m.label}</option>
                ))}
              </select>
            </FormField>
            <FormField label="Estado reacond.">
              <select className="input" value={editForm.estado_recon} onChange={fe('estado_recon')}>
                {Object.entries(RECON_META).map(([val, m]) => (
                  <option key={val} value={val}>{m.label}</option>
                ))}
              </select>
            </FormField>
          </div>
          <div style={{ marginTop: 14 }}>
            <FormField label="Notas internas">
              <textarea className="input" rows={3} value={editForm.notas_internas} onChange={fe('notas_internas')} style={{ resize: 'vertical' }} />
            </FormField>
          </div>
          <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', marginTop: 16 }}>
            <button className="btn secondary" onClick={() => setEditing(false)}>Cancelar</button>
            <button className="btn primary" onClick={saveEdit} disabled={saving}>
              {saving ? 'Guardando…' : <><Icon name="check" size={14} /> Guardar cambios</>}
            </button>
          </div>
        </Modal>
      )}

      {/* ── Modal seña desde panel derecho ── */}
      {showSideReservaModal && (
        <Modal title="Registrar seña" onClose={() => setShowSideReservaModal(false)}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <FormField label="Nombre cliente" required>
              <input className="input" value={reservaForm.cliente_nombre} onChange={fr('cliente_nombre')} placeholder="Juan Pérez" />
            </FormField>
            <FormField label="Teléfono">
              <input className="input" value={reservaForm.cliente_telefono} onChange={fr('cliente_telefono')} placeholder="+54 9 11…" />
            </FormField>
            <FormField label="Monto seña" required>
              <input className="input" type="number" value={reservaForm.monto_senia} onChange={fr('monto_senia')} min={0} />
            </FormField>
            <FormField label="Moneda">
              <select className="input" value={reservaForm.moneda} onChange={fr('moneda')}>
                <option value="USD">USD</option>
                <option value="ARS">ARS</option>
              </select>
            </FormField>
            <FormField label="Fecha vencimiento" hint="Si no paga antes de esta fecha la seña caduca">
              <input className="input" type="date" value={reservaForm.fecha_vencimiento} onChange={fr('fecha_vencimiento')} />
            </FormField>
            <FormField label="Notas">
              <input className="input" value={reservaForm.notas} onChange={fr('notas')} />
            </FormField>
          </div>
          <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', marginTop: 16 }}>
            <button className="btn secondary" onClick={() => setShowSideReservaModal(false)}>Cancelar</button>
            <button className="btn primary" onClick={submitReserva} disabled={savingReserva || !reservaForm.cliente_nombre || !reservaForm.monto_senia}>
              {savingReserva ? 'Registrando…' : <><Icon name="check" size={14} /> Guardar seña</>}
            </button>
          </div>
        </Modal>
      )}
    </div>
  )
}
