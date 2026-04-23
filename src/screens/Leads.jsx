import { useEffect, useState } from 'react'
import TopBar from '../components/TopBar'
import Modal from '../components/Modal'
import FormField from '../components/FormField'
import Icon from '../components/Icon'
import { getProspectos, createProspecto, updateProspecto, getVehiculos, getVendedores } from '../lib/supabase'

const ESTADOS = ['nuevo', 'contactado', 'visita_agendada', 'visita_realizada', 'convertido', 'descartado']
const CANALES = ['presencial', 'telegram', 'whatsapp', 'ml', 'web']
const ESTADO_COLOR = {
  nuevo: 'neutral', contactado: 'info', visita_agendada: 'warning',
  visita_realizada: 'warning', convertido: 'success', descartado: 'neutral',
}

function diasDesde(fechaStr) {
  if (!fechaStr) return null
  return Math.floor((Date.now() - new Date(fechaStr)) / 86400000)
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

const EMPTY_FORM = {
  nombre: '', telefono: '', email: '', canal: 'presencial',
  presupuesto_usd: '', interes: '', estado: 'nuevo',
  vehiculo_id: '', vendedor_id: '', notas: '',
}

export default function Leads({ onLogout }) {
  const [leads, setLeads]         = useState([])
  const [vehiculos, setVehiculos] = useState([])
  const [vendedores, setVendedores] = useState([])
  const [tab, setTab]             = useState('activos')
  const [modal, setModal]         = useState(null)
  const [saving, setSaving]       = useState(false)
  const [form, setForm]           = useState(EMPTY_FORM)

  // Filtros
  const [filtroCanal,    setFiltroCanal]    = useState('')
  const [filtroVendedor, setFiltroVendedor] = useState('')

  function reload() { getProspectos().then(setLeads) }

  useEffect(() => {
    reload()
    getVehiculos({ estado: 'disponible' }).then(setVehiculos)
    getVendedores().then(setVendedores)
  }, [])

  const f = (k) => (e) => setForm(p => ({ ...p, [k]: e.target.value }))

  function openNew()  { setForm(EMPTY_FORM); setModal('new') }
  function openEdit(lead) {
    setForm({
      nombre: lead.nombre || '', telefono: lead.telefono || '',
      email: lead.email || '', canal: lead.canal || 'presencial',
      presupuesto_usd: lead.presupuesto_usd || '', interes: lead.interes || '',
      estado: lead.estado || 'nuevo', vehiculo_id: lead.vehiculo_id || '',
      vendedor_id: lead.vendedor_id || '', notas: lead.notas || '',
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
      }
      if (modal === 'new') await createProspecto(payload)
      else await updateProspecto(modal.id, payload)
      reload(); setModal(null)
    } finally { setSaving(false) }
  }

  const activos    = leads.filter(l => !['convertido','descartado'].includes(l.estado))
  const convertidos = leads.filter(l => l.estado === 'convertido')

  function applyFiltros(list) {
    return list
      .filter(l => !filtroCanal    || l.canal    === filtroCanal)
      .filter(l => !filtroVendedor || l.vendedor_id === filtroVendedor)
  }

  const shown = applyFiltros(tab === 'activos' ? activos : tab === 'todos' ? leads : [])

  // Resumen
  const tasaConv = leads.length > 0 ? Math.round(convertidos.length / leads.length * 100) : 0
  const porCanal = CANALES.map(c => ({
    canal: c,
    total: leads.filter(l => l.canal === c).length,
    conv:  leads.filter(l => l.canal === c && l.estado === 'convertido').length,
  })).filter(x => x.total > 0)
  const porVendedor = vendedores.map(v => ({
    nombre: v.nombre,
    total:  leads.filter(l => l.vendedor_id === v.id).length,
    conv:   leads.filter(l => l.vendedor_id === v.id && l.estado === 'convertido').length,
  })).filter(x => x.total > 0)

  return (
    <div>
      <TopBar onLogout={onLogout} />
      <div className="main">
        <div className="page-head">
          <div>
            <h1 className="page-title">Leads</h1>
            <p className="page-caption">{activos.length} activos · {leads.length} total</p>
          </div>
          <div style={{ flex: 1 }} />
          <button className="btn primary" onClick={openNew}>
            <Icon name="plus" size={14} /> Nuevo lead
          </button>
        </div>

        {/* KPIs */}
        <div className="detail-head" style={{ marginBottom: 16 }}>
          {ESTADOS.slice(0, 4).map(e => (
            <div className="dm" key={e}>
              <div className="lbl">{e.replace(/_/g,' ')}</div>
              <div className="val">{activos.filter(l => l.estado === e).length}</div>
            </div>
          ))}
          <div className="dm">
            <div className="lbl">convertidos</div>
            <div className="val g">{convertidos.length}</div>
          </div>
          <div className="dm">
            <div className="lbl">tasa conv.</div>
            <div className="val g">{tasaConv}%</div>
          </div>
        </div>

        {/* Tabs */}
        <div className="tabs" style={{ marginBottom: 12 }}>
          {[['activos','Activos'], ['todos','Todos'], ['resumen','Resumen']].map(([k,l]) => (
            <button key={k} className={tab === k ? 'on' : ''} onClick={() => setTab(k)}>{l}</button>
          ))}
        </div>

        {/* Filtros (solo en activos/todos) */}
        {tab !== 'resumen' && (
          <div style={{ display: 'flex', gap: 10, marginBottom: 14, flexWrap: 'wrap' }}>
            <select className="input" style={{ width: 150 }} value={filtroCanal} onChange={e => setFiltroCanal(e.target.value)}>
              <option value="">Todos los canales</option>
              {CANALES.map(c => <option key={c} value={c}>{c}</option>)}
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
        )}

        {/* Tab Resumen */}
        {tab === 'resumen' ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(200px,1fr))', gap: 14 }}>
              <div className="card" style={{ padding: 16, textAlign: 'center' }}>
                <div style={{ fontSize: 28, fontWeight: 700 }}>{leads.length}</div>
                <div style={{ fontSize: 12, color: 'var(--c-fg-2)' }}>Leads totales</div>
              </div>
              <div className="card" style={{ padding: 16, textAlign: 'center' }}>
                <div style={{ fontSize: 28, fontWeight: 700 }}>{activos.length}</div>
                <div style={{ fontSize: 12, color: 'var(--c-fg-2)' }}>Activos</div>
              </div>
              <div className="card" style={{ padding: 16, textAlign: 'center' }}>
                <div style={{ fontSize: 28, fontWeight: 700, color: 'var(--c-success)' }}>{convertidos.length}</div>
                <div style={{ fontSize: 12, color: 'var(--c-fg-2)' }}>Convertidos</div>
              </div>
              <div className="card" style={{ padding: 16, textAlign: 'center' }}>
                <div style={{ fontSize: 28, fontWeight: 700, color: 'var(--c-success)' }}>{tasaConv}%</div>
                <div style={{ fontSize: 12, color: 'var(--c-fg-2)' }}>Tasa conversión</div>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
              <div className="card" style={{ padding: 16 }}>
                <h4 style={{ margin: '0 0 12px', fontSize: 13 }}>Por canal</h4>
                <table className="rank" style={{ fontSize: 12 }}>
                  <thead><tr><th>Canal</th><th className="num">Total</th><th className="num">Conv.</th><th className="num">Tasa</th></tr></thead>
                  <tbody>
                    {porCanal.map(r => (
                      <tr key={r.canal}>
                        <td style={{ textTransform: 'capitalize' }}>{r.canal}</td>
                        <td className="num">{r.total}</td>
                        <td className="num" style={{ color: 'var(--c-success)' }}>{r.conv}</td>
                        <td className="num">{r.total > 0 ? Math.round(r.conv / r.total * 100) : 0}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="card" style={{ padding: 16 }}>
                <h4 style={{ margin: '0 0 12px', fontSize: 13 }}>Por vendedor</h4>
                <table className="rank" style={{ fontSize: 12 }}>
                  <thead><tr><th>Vendedor</th><th className="num">Total</th><th className="num">Conv.</th><th className="num">Tasa</th></tr></thead>
                  <tbody>
                    {porVendedor.map(r => (
                      <tr key={r.nombre}>
                        <td>{r.nombre}</td>
                        <td className="num">{r.total}</td>
                        <td className="num" style={{ color: 'var(--c-success)' }}>{r.conv}</td>
                        <td className="num">{r.total > 0 ? Math.round(r.conv / r.total * 100) : 0}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="card" style={{ padding: 16 }}>
              <h4 style={{ margin: '0 0 12px', fontSize: 13 }}>Por estado (activos)</h4>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {ESTADOS.slice(0, 5).map(e => {
                  const n = leads.filter(l => l.estado === e).length
                  if (!n) return null
                  const pct = Math.round(n / leads.length * 100)
                  return (
                    <div key={e} style={{ flex: '1 1 120px', background: 'var(--c-bg-2)', borderRadius: 8, padding: '10px 14px' }}>
                      <div style={{ fontWeight: 600 }}>{n}</div>
                      <div style={{ fontSize: 11, color: 'var(--c-fg-2)', marginTop: 2 }}>{e.replace(/_/g,' ')}</div>
                      <div style={{ marginTop: 6, height: 4, borderRadius: 2, background: 'var(--c-border)' }}>
                        <div style={{ width: `${pct}%`, height: '100%', background: 'var(--c-accent)', borderRadius: 2 }} />
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>
        ) : shown.length === 0 ? (
          <div className="banner info"><Icon name="info" size={16} />No hay leads{tab === 'activos' ? ' activos' : ''} con esos filtros.</div>
        ) : (
          <table className="rank">
            <thead>
              <tr>
                <th>Nombre</th>
                <th>Canal</th>
                <th>Interés</th>
                <th className="num">Presupuesto</th>
                <th>Estado</th>
                <th>Días</th>
                <th>Vendedor</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {shown.map(lead => (
                <tr key={lead.id}>
                  <td>
                    <strong>{lead.nombre}</strong>
                    {lead.telefono && <div style={{ fontSize: 11, color: 'var(--c-fg-2)' }}>{lead.telefono}</div>}
                  </td>
                  <td style={{ fontSize: 12, color: 'var(--c-fg-2)', textTransform: 'capitalize' }}>{lead.canal}</td>
                  <td style={{ fontSize: 12, color: 'var(--c-fg-2)' }}>
                    {lead.vehiculos
                      ? `${lead.vehiculos.marca} ${lead.vehiculos.modelo} ${lead.vehiculos.anio}`
                      : lead.interes || '—'}
                  </td>
                  <td className="num" style={{ fontSize: 13 }}>
                    {lead.presupuesto_usd ? `USD ${Number(lead.presupuesto_usd).toLocaleString('es-AR')}` : '—'}
                  </td>
                  <td>
                    <span className={`badge ${ESTADO_COLOR[lead.estado] || 'neutral'}`}>
                      <span className="cdot" /> {lead.estado.replace(/_/g,' ')}
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
              ))}
            </tbody>
          </table>
        )}
      </div>

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
              <FormField label="Canal">
                <select className="input" value={form.canal} onChange={f('canal')}>
                  {CANALES.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              </FormField>
              <FormField label="Estado">
                <select className="input" value={form.estado} onChange={f('estado')}>
                  {ESTADOS.map(e => <option key={e} value={e}>{e.replace(/_/g,' ')}</option>)}
                </select>
              </FormField>
              <FormField label="Presupuesto (USD)">
                <input className="input" type="number" value={form.presupuesto_usd} onChange={f('presupuesto_usd')} placeholder="15000" />
              </FormField>
              <FormField label="Interés (texto libre)">
                <input className="input" value={form.interes} onChange={f('interes')} placeholder="Toyota Corolla 2020" />
              </FormField>
              <FormField label="Vehículo en stock">
                <select className="input" value={form.vehiculo_id} onChange={f('vehiculo_id')}>
                  <option value="">— ninguno —</option>
                  {vehiculos.map(v => (
                    <option key={v.id} value={v.id}>{v.marca} {v.modelo} {v.anio} — USD {v.precio_base?.toLocaleString('es-AR')}</option>
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
