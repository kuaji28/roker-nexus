import { useEffect, useState } from 'react'
import TopBar from '../components/TopBar'
import Modal from '../components/Modal'
import FormField from '../components/FormField'
import Icon from '../components/Icon'
import { getProspectos, createProspecto, updateProspecto, getVehiculos, getVendedores, supabase } from '../lib/supabase'

// ─── Pipeline stages ───────────────────────────────────────────────────────
const STAGES = ['nuevo', 'en_contacto', 'con_propuesta', 'cerrado', 'perdido']

const STAGE_META = {
  nuevo:         { label: 'Nuevo',         color: '#4D9DE0', bg: '#EBF5FB', icon: '🆕' },
  en_contacto:   { label: 'En contacto',   color: '#F5A623', bg: '#FEF9EE', icon: '💬' },
  con_propuesta: { label: 'Con propuesta', color: '#F97316', bg: '#FFF4ED', icon: '📋' },
  cerrado:       { label: 'Cerrado',       color: '#00C48C', bg: '#EAFAF4', icon: '✅' },
  perdido:       { label: 'Perdido',       color: '#6B7280', bg: '#F3F4F6', icon: '❌' },
}

// ─── Canales ────────────────────────────────────────────────────────────────
const CANAL_META = {
  mercadolibre: { label: 'MercadoLibre', color: '#FFE600', textColor: '#000' },
  instagram:    { label: 'Instagram',    color: '#E1306C', textColor: '#fff' },
  facebook:     { label: 'Facebook',     color: '#1877F2', textColor: '#fff' },
  whatsapp:     { label: 'WhatsApp',     color: '#25D366', textColor: '#fff' },
  referido:     { label: 'Referido',     color: '#8B5CF6', textColor: '#fff' },
  showroom:     { label: 'Showroom',     color: '#00C48C', textColor: '#fff' },
  web:          { label: 'Web',          color: '#4D9DE0', textColor: '#fff' },
  // legacy (de la versión anterior)
  presencial:   { label: 'Presencial',   color: '#00C48C', textColor: '#fff' },
  telegram:     { label: 'Telegram',     color: '#26A5E4', textColor: '#fff' },
  ml:           { label: 'MercadoLibre', color: '#FFE600', textColor: '#000' },
}

const CANALES_NUEVOS = ['mercadolibre', 'instagram', 'facebook', 'whatsapp', 'referido', 'showroom', 'web']

// ─── Legacy (estados anteriores, solo para compatibilidad) ──────────────────
const ESTADOS_LEGACY = ['nuevo', 'contactado', 'visita_agendada', 'visita_realizada', 'convertido', 'descartado']

// ─── Helpers ────────────────────────────────────────────────────────────────
function diasDesde(fechaStr) {
  if (!fechaStr) return null
  return Math.floor((Date.now() - new Date(fechaStr)) / 86400000)
}

function iniciales(nombre) {
  if (!nombre) return '?'
  const parts = nombre.trim().split(' ')
  return parts.length >= 2
    ? (parts[0][0] + parts[1][0]).toUpperCase()
    : nombre.slice(0, 2).toUpperCase()
}

function stageFromLead(lead) {
  // Si ya tiene stage nuevo → usar
  if (lead.stage) return lead.stage
  // Migrar desde estado legacy
  const map = {
    nuevo: 'nuevo', contactado: 'en_contacto',
    visita_agendada: 'con_propuesta', visita_realizada: 'con_propuesta',
    convertido: 'cerrado', descartado: 'perdido',
  }
  return map[lead.estado] || 'nuevo'
}

function canalDisplay(lead) {
  return lead.canal_origen || lead.canal || null
}

async function moverStage(prospectoId, nuevoStage) {
  await supabase.from('prospectos').update({ stage: nuevoStage }).eq('id', prospectoId)
}

// ─── Sub-components ─────────────────────────────────────────────────────────
function CanalBadge({ canal }) {
  if (!canal) return null
  const meta = CANAL_META[canal] || { label: canal, color: '#ccc', textColor: '#000' }
  return (
    <span style={{
      display: 'inline-block', fontSize: 10, fontWeight: 600, padding: '2px 7px',
      borderRadius: 20, background: meta.color, color: meta.textColor,
      letterSpacing: 0.3, lineHeight: 1.5,
    }}>
      {meta.label}
    </span>
  )
}

function SemaforoBadge({ fecha }) {
  const d = diasDesde(fecha)
  if (d === null) return null
  const cls = d < 7 ? 'success' : d < 14 ? 'info' : d < 30 ? 'warning' : 'danger'
  return (
    <span className={`badge ${cls}`} style={{ fontSize: 11 }}>
      <span className="cdot" /> {d}d
    </span>
  )
}

function Avatar({ nombre }) {
  return (
    <div style={{
      width: 32, height: 32, borderRadius: '50%', background: 'var(--c-accent)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      color: '#fff', fontWeight: 700, fontSize: 12, flexShrink: 0,
    }}>
      {iniciales(nombre)}
    </div>
  )
}

// ─── Lead Card (Kanban) ──────────────────────────────────────────────────────
function LeadCard({ lead, stageKey, vendedores, onEdit, onMover, onReload }) {
  const stages = STAGES
  const idx = stages.indexOf(stageKey)
  const canal = canalDisplay(lead)
  const nombreVendedor = vendedores.find(v => v.id === lead.vendedor_id)?.nombre

  function whatsapp() {
    const tel = (lead.telefono || '').replace(/\D/g, '')
    if (!tel) return
    window.open(`https://wa.me/${tel}`, '_blank')
  }

  async function avanzar() {
    if (idx >= stages.length - 1) return
    const next = stages[idx + 1]
    await moverStage(lead.id, next)
    onReload()
  }

  async function retroceder() {
    if (idx <= 0) return
    const prev = stages[idx - 1]
    await moverStage(lead.id, prev)
    onReload()
  }

  const meta = STAGE_META[stageKey]

  return (
    <div className="card" style={{
      padding: '10px 12px', marginBottom: 8, cursor: 'default',
      borderLeft: `3px solid ${meta.color}`, fontSize: 12,
    }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8, marginBottom: 6 }}>
        <Avatar nombre={lead.nombre} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontWeight: 600, fontSize: 13, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {lead.nombre}
          </div>
          {lead.telefono && (
            <div style={{ color: 'var(--c-fg-2)', fontSize: 11 }}>{lead.telefono}</div>
          )}
        </div>
        <SemaforoBadge fecha={lead.updated_at || lead.created_at} />
      </div>

      {/* Canal + vehículo */}
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 6, alignItems: 'center' }}>
        {canal && <CanalBadge canal={canal} />}
        {lead.presupuesto_usd && (
          <span style={{ fontSize: 11, color: 'var(--c-fg-2)' }}>
            USD {Number(lead.presupuesto_usd).toLocaleString('es-AR')}
          </span>
        )}
      </div>

      {/* Vehículo de interés */}
      {(lead.vehiculos || lead.interes) && (
        <div style={{ fontSize: 11, color: 'var(--c-fg-2)', marginBottom: 4 }}>
          🚗 {lead.vehiculos
            ? `${lead.vehiculos.marca} ${lead.vehiculos.modelo} ${lead.vehiculos.anio}`
            : lead.interes}
        </div>
      )}

      {/* Vendedor */}
      {nombreVendedor && (
        <div style={{ fontSize: 11, color: 'var(--c-fg-2)', marginBottom: 6 }}>
          👤 {nombreVendedor}
        </div>
      )}

      {/* Fecha próximo contacto */}
      {lead.fecha_proximo_contacto && (
        <div style={{ fontSize: 11, color: 'var(--c-accent)', marginBottom: 6 }}>
          📅 {new Date(lead.fecha_proximo_contacto + 'T00:00:00').toLocaleDateString('es-AR')}
        </div>
      )}

      {/* Acciones */}
      <div style={{ display: 'flex', gap: 4, marginTop: 6, flexWrap: 'wrap' }}>
        {idx > 0 && (
          <button className="btn ghost" style={{ fontSize: 10, padding: '2px 6px' }} onClick={retroceder} title="Retroceder stage">
            ◀
          </button>
        )}
        {idx < stages.length - 1 && (
          <button className="btn ghost" style={{ fontSize: 10, padding: '2px 6px' }} onClick={avanzar} title="Avanzar stage">
            ▶
          </button>
        )}
        {lead.telefono && (
          <button className="btn ghost" style={{ fontSize: 10, padding: '2px 6px' }} onClick={whatsapp} title="Abrir WhatsApp">
            💬
          </button>
        )}
        <button className="btn ghost" style={{ fontSize: 10, padding: '2px 6px' }} onClick={() => onEdit(lead)} title="Editar">
          ✏️
        </button>
      </div>
    </div>
  )
}

// ─── Columna Kanban ──────────────────────────────────────────────────────────
function KanbanCol({ stageKey, leads, vendedores, onEdit, onMover, onReload, onNuevoEnStage }) {
  const meta = STAGE_META[stageKey]
  const totalUSD = leads.reduce((sum, l) => sum + (Number(l.presupuesto_usd) || 0), 0)

  return (
    <div style={{
      flex: '1 1 200px', minWidth: 200, maxWidth: 280,
      display: 'flex', flexDirection: 'column',
    }}>
      {/* Header columna */}
      <div style={{
        background: meta.bg, borderRadius: '8px 8px 0 0',
        padding: '8px 12px', marginBottom: 2,
        borderTop: `3px solid ${meta.color}`,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ fontSize: 14 }}>{meta.icon}</span>
          <span style={{ fontWeight: 700, fontSize: 12, color: meta.color }}>{meta.label}</span>
          <span style={{
            marginLeft: 'auto', background: meta.color, color: '#fff',
            borderRadius: 20, fontSize: 11, fontWeight: 700, padding: '1px 7px',
          }}>
            {leads.length}
          </span>
        </div>
        {totalUSD > 0 && (
          <div style={{ fontSize: 10, color: 'var(--c-fg-2)', marginTop: 2 }}>
            USD {totalUSD.toLocaleString('es-AR')}
          </div>
        )}
      </div>

      {/* Cards */}
      <div style={{
        flex: 1, background: 'var(--c-bg-2)', borderRadius: '0 0 8px 8px',
        padding: '8px 8px 4px', minHeight: 80,
      }}>
        {leads.map(lead => (
          <LeadCard
            key={lead.id}
            lead={lead}
            stageKey={stageKey}
            vendedores={vendedores}
            onEdit={onEdit}
            onMover={onMover}
            onReload={onReload}
          />
        ))}

        {/* Agregar en este stage */}
        <button
          className="btn ghost"
          style={{ width: '100%', fontSize: 11, marginTop: 4, padding: '6px 0', opacity: 0.7 }}
          onClick={() => onNuevoEnStage(stageKey)}
        >
          + Agregar lead
        </button>
      </div>
    </div>
  )
}

// ─── Form inicial ────────────────────────────────────────────────────────────
const EMPTY_FORM = {
  nombre: '', telefono: '', email: '',
  canal: 'presencial',            // campo legacy
  canal_origen: 'whatsapp',       // campo nuevo
  presupuesto_usd: '', interes: '',
  estado: 'nuevo',                // campo legacy
  stage: 'nuevo',                 // campo nuevo
  vehiculo_id: '', vendedor_id: '',
  fecha_proximo_contacto: '',
  notas: '',
}

// ─── Componente principal ────────────────────────────────────────────────────
export default function Leads({ onLogout }) {
  const [leads, setLeads]         = useState([])
  const [vehiculos, setVehiculos] = useState([])
  const [vendedores, setVendedores] = useState([])
  const [vista, setVista]         = useState('pipeline') // 'pipeline' | 'lista' | 'resumen'
  const [modal, setModal]         = useState(null)
  const [saving, setSaving]       = useState(false)
  const [form, setForm]           = useState(EMPTY_FORM)

  // Filtros (vista lista)
  const [filtroCanal,    setFiltroCanal]    = useState('')
  const [filtroVendedor, setFiltroVendedor] = useState('')

  function reload() { getProspectos().then(setLeads) }

  useEffect(() => {
    reload()
    getVehiculos({ estado: 'disponible' }).then(setVehiculos)
    getVendedores().then(setVendedores)
  }, [])

  const f = (k) => (e) => setForm(p => ({ ...p, [k]: e.target.value }))

  function openNew(stageInicial = 'nuevo') {
    setForm({ ...EMPTY_FORM, stage: stageInicial })
    setModal('new')
  }

  function openEdit(lead) {
    setForm({
      nombre: lead.nombre || '', telefono: lead.telefono || '',
      email: lead.email || '',
      canal: lead.canal || 'presencial',
      canal_origen: lead.canal_origen || lead.canal || 'whatsapp',
      presupuesto_usd: lead.presupuesto_usd || '',
      interes: lead.interes || '',
      estado: lead.estado || 'nuevo',
      stage: stageFromLead(lead),
      vehiculo_id: lead.vehiculo_id || '',
      vendedor_id: lead.vendedor_id || '',
      fecha_proximo_contacto: lead.fecha_proximo_contacto || '',
      notas: lead.notas || '',
    })
    setModal(lead)
  }

  async function save() {
    if (!form.nombre) return
    setSaving(true)
    try {
      const payload = {
        ...form,
        presupuesto_usd: form.presupuesto_usd ? Number(form.presupuesto_usd) : null,
        vehiculo_id: form.vehiculo_id || null,
        vendedor_id: form.vendedor_id || null,
        fecha_proximo_contacto: form.fecha_proximo_contacto || null,
      }
      if (modal === 'new') await createProspecto(payload)
      else await updateProspecto(modal.id, payload)
      reload(); setModal(null)
    } finally { setSaving(false) }
  }

  // ── Datos derivados ──
  const leadsConStage = leads.map(l => ({ ...l, _stage: stageFromLead(l) }))
  const activos       = leadsConStage.filter(l => !['cerrado','perdido'].includes(l._stage))
  const cerrados      = leadsConStage.filter(l => l._stage === 'cerrado')
  const tasaConv      = leads.length > 0 ? Math.round(cerrados.length / leads.length * 100) : 0

  function leadsByStage(s) { return leadsConStage.filter(l => l._stage === s) }

  // Filtros vista lista
  function applyFiltros(list) {
    return list
      .filter(l => !filtroCanal    || canalDisplay(l) === filtroCanal)
      .filter(l => !filtroVendedor || l.vendedor_id  === filtroVendedor)
  }
  const listaShown = applyFiltros(leadsConStage)

  // Por canal (resumen)
  const todosCanales = [...new Set(leadsConStage.map(l => canalDisplay(l)).filter(Boolean))]
  const porCanal = todosCanales.map(c => ({
    canal: c,
    total: leadsConStage.filter(l => canalDisplay(l) === c).length,
    conv:  leadsConStage.filter(l => canalDisplay(l) === c && l._stage === 'cerrado').length,
  }))
  const porVendedor = vendedores.map(v => ({
    nombre: v.nombre,
    total:  leadsConStage.filter(l => l.vendedor_id === v.id).length,
    conv:   leadsConStage.filter(l => l.vendedor_id === v.id && l._stage === 'cerrado').length,
  })).filter(x => x.total > 0)

  return (
    <div>
      <TopBar onLogout={onLogout} />
      <div className="main">

        {/* Page head */}
        <div className="page-head">
          <div>
            <h1 className="page-title">Leads</h1>
            <p className="page-caption">{activos.length} activos · {leads.length} total</p>
          </div>
          <div style={{ flex: 1 }} />

          {/* Selector de vista */}
          <div style={{ display: 'flex', gap: 4, marginRight: 12 }}>
            {[['pipeline','🗂 Pipeline'],['lista','📋 Lista'],['resumen','📊 Resumen']].map(([k,l]) => (
              <button
                key={k}
                className={`btn ${vista === k ? 'primary' : 'secondary'}`}
                style={{ fontSize: 12, padding: '5px 12px' }}
                onClick={() => setVista(k)}
              >
                {l}
              </button>
            ))}
          </div>

          <button className="btn primary" onClick={() => openNew()}>
            <Icon name="plus" size={14} /> Nuevo lead
          </button>
        </div>

        {/* KPIs */}
        <div className="detail-head" style={{ marginBottom: 16 }}>
          {STAGES.map(s => {
            const n = leadsByStage(s).length
            const meta = STAGE_META[s]
            return (
              <div className="dm" key={s} style={{ cursor: 'pointer' }} onClick={() => setVista('pipeline')}>
                <div className="lbl">{meta.icon} {meta.label}</div>
                <div className="val" style={{ color: meta.color }}>{n}</div>
              </div>
            )
          })}
          <div className="dm">
            <div className="lbl">tasa conv.</div>
            <div className="val g">{tasaConv}%</div>
          </div>
        </div>

        {/* ══ VISTA PIPELINE ══════════════════════════════════════════════════ */}
        {vista === 'pipeline' && (
          <div style={{
            display: 'flex', gap: 10, overflowX: 'auto',
            paddingBottom: 16, alignItems: 'flex-start',
          }}>
            {STAGES.map(s => (
              <KanbanCol
                key={s}
                stageKey={s}
                leads={leadsByStage(s)}
                vendedores={vendedores}
                onEdit={openEdit}
                onReload={reload}
                onNuevoEnStage={openNew}
              />
            ))}
          </div>
        )}

        {/* ══ VISTA LISTA ═════════════════════════════════════════════════════ */}
        {vista === 'lista' && (
          <>
            {/* Filtros */}
            <div style={{ display: 'flex', gap: 10, marginBottom: 14, flexWrap: 'wrap' }}>
              <select className="input" style={{ width: 150 }} value={filtroCanal} onChange={e => setFiltroCanal(e.target.value)}>
                <option value="">Todos los canales</option>
                {todosCanales.map(c => (
                  <option key={c} value={c}>{CANAL_META[c]?.label || c}</option>
                ))}
              </select>
              <select className="input" style={{ width: 180 }} value={filtroVendedor} onChange={e => setFiltroVendedor(e.target.value)}>
                <option value="">Todos los vendedores</option>
                {vendedores.map(v => <option key={v.id} value={v.id}>{v.nombre}</option>)}
              </select>
              {(filtroCanal || filtroVendedor) && (
                <button className="btn ghost" onClick={() => { setFiltroCanal(''); setFiltroVendedor('') }}>
                  Limpiar
                </button>
              )}
            </div>

            {listaShown.length === 0 ? (
              <div className="banner info">
                <Icon name="info" size={16} />No hay leads con esos filtros.
              </div>
            ) : (
              <table className="rank">
                <thead>
                  <tr>
                    <th>Nombre</th>
                    <th>Canal</th>
                    <th>Interés</th>
                    <th className="num">Presupuesto</th>
                    <th>Stage</th>
                    <th>Días</th>
                    <th>Vendedor</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {listaShown.map(lead => {
                    const meta = STAGE_META[lead._stage]
                    return (
                      <tr key={lead.id}>
                        <td>
                          <strong>{lead.nombre}</strong>
                          {lead.telefono && <div style={{ fontSize: 11, color: 'var(--c-fg-2)' }}>{lead.telefono}</div>}
                        </td>
                        <td><CanalBadge canal={canalDisplay(lead)} /></td>
                        <td style={{ fontSize: 12, color: 'var(--c-fg-2)' }}>
                          {lead.vehiculos
                            ? `${lead.vehiculos.marca} ${lead.vehiculos.modelo} ${lead.vehiculos.anio}`
                            : lead.interes || '—'}
                        </td>
                        <td className="num" style={{ fontSize: 13 }}>
                          {lead.presupuesto_usd ? `USD ${Number(lead.presupuesto_usd).toLocaleString('es-AR')}` : '—'}
                        </td>
                        <td>
                          <span style={{
                            display: 'inline-block', fontSize: 11, fontWeight: 600, padding: '2px 8px',
                            borderRadius: 20, background: meta.bg, color: meta.color,
                          }}>
                            {meta.icon} {meta.label}
                          </span>
                        </td>
                        <td><SemaforoBadge fecha={lead.updated_at || lead.created_at} /></td>
                        <td style={{ fontSize: 12, color: 'var(--c-fg-2)' }}>{lead.vendedores?.nombre || '—'}</td>
                        <td>
                          <button className="btn ghost" onClick={() => openEdit(lead)}>
                            <Icon name="edit" size={14} />
                          </button>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            )}
          </>
        )}

        {/* ══ VISTA RESUMEN ═══════════════════════════════════════════════════ */}
        {vista === 'resumen' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            {/* Métricas globales */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(180px,1fr))', gap: 14 }}>
              <div className="card" style={{ padding: 16, textAlign: 'center' }}>
                <div style={{ fontSize: 28, fontWeight: 700 }}>{leads.length}</div>
                <div style={{ fontSize: 12, color: 'var(--c-fg-2)' }}>Leads totales</div>
              </div>
              <div className="card" style={{ padding: 16, textAlign: 'center' }}>
                <div style={{ fontSize: 28, fontWeight: 700 }}>{activos.length}</div>
                <div style={{ fontSize: 12, color: 'var(--c-fg-2)' }}>Activos</div>
              </div>
              <div className="card" style={{ padding: 16, textAlign: 'center' }}>
                <div style={{ fontSize: 28, fontWeight: 700, color: '#00C48C' }}>{cerrados.length}</div>
                <div style={{ fontSize: 12, color: 'var(--c-fg-2)' }}>Cerrados</div>
              </div>
              <div className="card" style={{ padding: 16, textAlign: 'center' }}>
                <div style={{ fontSize: 28, fontWeight: 700, color: '#00C48C' }}>{tasaConv}%</div>
                <div style={{ fontSize: 12, color: 'var(--c-fg-2)' }}>Tasa conversión</div>
              </div>
            </div>

            {/* Por stage */}
            <div className="card" style={{ padding: 16 }}>
              <h4 style={{ margin: '0 0 12px', fontSize: 13 }}>Distribución por stage</h4>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {STAGES.map(s => {
                  const n = leadsByStage(s).length
                  if (!n) return null
                  const pct = Math.round(n / leads.length * 100)
                  const meta = STAGE_META[s]
                  return (
                    <div key={s} style={{
                      flex: '1 1 120px', background: meta.bg,
                      border: `1px solid ${meta.color}33`,
                      borderRadius: 8, padding: '10px 14px',
                    }}>
                      <div style={{ fontWeight: 600, color: meta.color }}>{n}</div>
                      <div style={{ fontSize: 11, color: 'var(--c-fg-2)', marginTop: 2 }}>
                        {meta.icon} {meta.label}
                      </div>
                      <div style={{ marginTop: 6, height: 4, borderRadius: 2, background: 'var(--c-border)' }}>
                        <div style={{ width: `${pct}%`, height: '100%', background: meta.color, borderRadius: 2 }} />
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Por canal y por vendedor */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
              <div className="card" style={{ padding: 16 }}>
                <h4 style={{ margin: '0 0 12px', fontSize: 13 }}>Por canal</h4>
                <table className="rank" style={{ fontSize: 12 }}>
                  <thead>
                    <tr><th>Canal</th><th className="num">Total</th><th className="num">Cerr.</th><th className="num">Tasa</th></tr>
                  </thead>
                  <tbody>
                    {porCanal.map(r => (
                      <tr key={r.canal}>
                        <td><CanalBadge canal={r.canal} /></td>
                        <td className="num">{r.total}</td>
                        <td className="num" style={{ color: '#00C48C' }}>{r.conv}</td>
                        <td className="num">{r.total > 0 ? Math.round(r.conv / r.total * 100) : 0}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="card" style={{ padding: 16 }}>
                <h4 style={{ margin: '0 0 12px', fontSize: 13 }}>Por vendedor</h4>
                <table className="rank" style={{ fontSize: 12 }}>
                  <thead>
                    <tr><th>Vendedor</th><th className="num">Total</th><th className="num">Cerr.</th><th className="num">Tasa</th></tr>
                  </thead>
                  <tbody>
                    {porVendedor.map(r => (
                      <tr key={r.nombre}>
                        <td>{r.nombre}</td>
                        <td className="num">{r.total}</td>
                        <td className="num" style={{ color: '#00C48C' }}>{r.conv}</td>
                        <td className="num">{r.total > 0 ? Math.round(r.conv / r.total * 100) : 0}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ══ MODAL ══════════════════════════════════════════════════════════════ */}
      {modal && (
        <Modal title={modal === 'new' ? 'Nuevo lead' : 'Editar lead'} onClose={() => setModal(null)}>
          <div style={{ display: 'grid', gap: 12 }}>
            <FormField label="Nombre" required>
              <input className="input" value={form.nombre} onChange={f('nombre')} placeholder="Juan Pérez" />
            </FormField>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <FormField label="Teléfono">
                <input className="input" value={form.telefono} onChange={f('telefono')} placeholder="+54 9 11..." />
              </FormField>
              <FormField label="Email">
                <input className="input" type="email" value={form.email} onChange={f('email')} />
              </FormField>

              <FormField label="Canal de origen">
                <select className="input" value={form.canal_origen} onChange={f('canal_origen')}>
                  {CANALES_NUEVOS.map(c => (
                    <option key={c} value={c}>{CANAL_META[c]?.label || c}</option>
                  ))}
                </select>
              </FormField>

              <FormField label="Stage">
                <select className="input" value={form.stage} onChange={f('stage')}>
                  {STAGES.map(s => (
                    <option key={s} value={s}>{STAGE_META[s].icon} {STAGE_META[s].label}</option>
                  ))}
                </select>
              </FormField>

              <FormField label="Presupuesto (USD)">
                <input className="input" type="number" value={form.presupuesto_usd} onChange={f('presupuesto_usd')} placeholder="15000" />
              </FormField>

              <FormField label="Próximo contacto">
                <input className="input" type="date" value={form.fecha_proximo_contacto} onChange={f('fecha_proximo_contacto')} />
              </FormField>

              <FormField label="Interés (texto libre)">
                <input className="input" value={form.interes} onChange={f('interes')} placeholder="Toyota Corolla 2020" />
              </FormField>

              <FormField label="Vehículo en stock">
                <select className="input" value={form.vehiculo_id} onChange={f('vehiculo_id')}>
                  <option value="">— ninguno —</option>
                  {vehiculos.map(v => (
                    <option key={v.id} value={v.id}>
                      {v.marca} {v.modelo} {v.anio} — USD {v.precio_base?.toLocaleString('es-AR')}
                    </option>
                  ))}
                </select>
              </FormField>

              <FormField label="Vendedor">
                <select className="input" value={form.vendedor_id} onChange={f('vendedor_id')}>
                  <option value="">— ninguno —</option>
                  {vendedores.map(v => <option key={v.id} value={v.id}>{v.nombre}</option>)}
                </select>
              </FormField>
            </div>

            <FormField label="Notas">
              <textarea className="input" rows={2} value={form.notas} onChange={f('notas')} style={{ resize: 'vertical' }} />
            </FormField>

            <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
              <button className="btn secondary" onClick={() => setModal(null)}>Cancelar</button>
              <button className="btn primary" onClick={save} disabled={saving || !form.nombre}>
                {saving ? 'Guardando…' : <><Icon name="check" size={14} /> Guardar</>}
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  )
}
