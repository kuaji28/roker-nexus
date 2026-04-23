import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import TopBar from '../components/TopBar'
import StateBadge from '../components/StateBadge'
import Icon from '../components/Icon'
import Modal from '../components/Modal'
import FormField from '../components/FormField'
import { getVehiculo, updateVehiculo, getGastosByVehiculo, createGasto, getReservasByVehiculo, createReserva, getDocumentacion, upsertDocumentacion } from '../lib/supabase'
import { callAI, callAIFiles, aiConfigured } from '../lib/api'
import { useTc } from '../hooks/useTc'

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

export default function Detalle({ onLogout }) {
  const { id }   = useParams()
  const navigate = useNavigate()
  const TC       = useTc()

  // ── ALL hooks before any conditional return ──────────────────
  const [data, setData]     = useState(null)
  const [tab, setTab]       = useState('info')
  const [foto, setFoto]     = useState(0)

  const [editing, setEditing]   = useState(false)
  const [editForm, setEditForm] = useState({})
  const [saving, setSaving]     = useState(false)

  const [aiModal, setAiModal]     = useState(null)
  const [aiResult, setAiResult]   = useState('')
  const [aiLoading, setAiLoading] = useState(false)

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

  useEffect(() => {
    Promise.all([
      getVehiculo(id),
      getGastosByVehiculo(id),
      getReservasByVehiculo(id),
      getDocumentacion(id),
    ]).then(([d, g, r, doc]) => {
      setData(d); setGastos(g); setReservas(r)
      const docData = doc || {}
      setDocs(docData)
      setDocsForm(docData)
    })
  }, [id])

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

  // ── Loading state ─────────────────────────────────────────────
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

  // ── Derived values ────────────────────────────────────────────
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

  // ── Handlers ──────────────────────────────────────────────────
  function openEdit() {
    setEditForm({
      marca: v.marca, modelo: v.modelo, anio: v.anio,
      version: v.version || '', color: v.color || '',
      km_hs: v.km_hs || '', precio_base: v.precio_base || '',
      costo_compra: v.costo_compra || '', estado: v.estado,
      combustible: v.combustible || '', transmision: v.transmision || '',
      patente: v.patente || '', notas_internas: v.notas_internas || '',
      link_ml: v.link_ml || '', link_drive: v.link_drive || '',
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
      setReservaForm(EMPTY_RESERVA)
    } finally { setSavingReserva(false) }
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
            <h1 className="page-title">{v.marca} {v.modelo} {v.anio}</h1>
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
          </>}
          <button className="btn primary" onClick={openEdit}><Icon name="edit" size={14} />Editar</button>
        </div>

        <div className="detail-head">
          <div className="dm">
            <div className="lbl">Estado</div>
            <div className="val" style={{ fontSize: 16 }}><StateBadge estado={v.estado} /></div>
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

        <div className="tabs">
          {[
            ['info', 'info', 'Información'],
            ['fotos', 'image', fotos.length > 0 ? `Fotos (${fotos.length})` : 'Fotos'],
            ['gastos', 'cash', gastos.length > 0 ? `Gastos (${gastos.length})` : 'Gastos'],
            ['res', 'users', reservas.length > 0 ? `Reservas (${reservas.length})` : 'Reservas'],
            ['docs', 'doc', 'Documentación'],
          ].map(([k, ic, l]) => (
            <button key={k} className={tab === k ? 'on' : ''} onClick={() => setTab(k)}>
              <Icon name={ic} size={13} />{l}
            </button>
          ))}
        </div>

        {/* ── TAB: INFO ── */}
        {tab === 'info' && (
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
    </div>
  )
}
