import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import TopBar from '../components/TopBar'
import VehicleCard from '../components/VehicleCard'
import StateBadge from '../components/StateBadge'
import Icon from '../components/Icon'
import { getVehiculos, updateVehiculo } from '../lib/supabase'
import { useTc } from '../hooks/useTc'

const ESTADOS      = ['todos', 'disponible', 'señado', 'en_revision', 'en_preparacion', 'vendido']
const TIPOS        = ['todos', 'auto', 'moto', 'cuatriciclo', 'moto_de_agua']
const ESTADOS_EDIT = ['disponible', 'señado', 'en_revision', 'en_preparacion', 'vendido']

export default function Catalogo({ onLogout }) {
  const navigate = useNavigate()
  const TC = useTc()
  const [params] = useSearchParams()

  const [vehiculos, setVehiculos] = useState([])
  const [loading, setLoading]     = useState(true)
  const [view, setView]           = useState('cards')

  // Filtros texto/select
  const [search, setSearch] = useState(params.get('search') || '')
  const [estado, setEstado] = useState(params.get('estado') || 'todos')
  const [tipo, setTipo]     = useState('todos')

  // Filtros numéricos
  const [anioMin,    setAnioMin]    = useState('')
  const [anioMax,    setAnioMax]    = useState('')
  const [kmMax,      setKmMax]      = useState('')
  const [precioMin,  setPrecioMin]  = useState('')
  const [precioMax,  setPrecioMax]  = useState('')
  const [filtrosExp, setFiltrosExp] = useState(false)

  // Edición inline
  const [editId,    setEditId]    = useState(null)
  const [editForm,  setEditForm]  = useState({})
  const [savingId,  setSavingId]  = useState(null)

  function reload() {
    setLoading(true)
    getVehiculos({ estado, tipo, search }).then(data => {
      setVehiculos(data)
      setLoading(false)
    })
  }

  useEffect(() => { reload() }, [estado, tipo, search])

  // Filtrado numérico client-side
  const shown = vehiculos.filter(v => {
    if (anioMin  && v.anio       <  Number(anioMin))  return false
    if (anioMax  && v.anio       >  Number(anioMax))  return false
    if (kmMax    && v.km_hs      >  Number(kmMax))    return false
    if (precioMin && (v.precio_base || 0) < Number(precioMin)) return false
    if (precioMax && (v.precio_base || 0) > Number(precioMax)) return false
    return true
  })

  const numFiltrosActivos = [anioMin, anioMax, kmMax, precioMin, precioMax].filter(Boolean).length

  function startEdit(v, e) {
    e.stopPropagation()
    setEditId(v.id)
    setEditForm({ estado: v.estado, km_hs: v.km_hs || '', precio_base: v.precio_base || '' })
  }
  function cancelEdit(e) { e?.stopPropagation(); setEditId(null) }

  async function saveEdit(id, e) {
    e.stopPropagation()
    setSavingId(id)
    try {
      await updateVehiculo(id, {
        estado:      editForm.estado,
        km_hs:       editForm.km_hs    ? Number(editForm.km_hs)    : null,
        precio_base: editForm.precio_base ? Number(editForm.precio_base) : null,
      })
      reload()
      setEditId(null)
    } finally { setSavingId(null) }
  }

  return (
    <div>
      <TopBar placeholder="Marca, modelo, patente…" onLogout={onLogout} />
      <div className="main">
        <div className="page-head">
          <div>
            <h1 className="page-title">Catálogo</h1>
            <p className="page-caption">{shown.length} vehículo(s)</p>
          </div>
          <div style={{ flex: 1 }} />
          <button className="btn primary" onClick={() => navigate('/ingreso')}>
            <Icon name="plus" size={14} /> Ingresar vehículo
          </button>
        </div>

        {/* ── Barra de filtros ── */}
        <div className="filter-card">
          <div className="filter-row">
            <div>
              <label>Buscar</label>
              <div className="search-field" style={{ background: 'var(--c-bg)' }}>
                <Icon name="search" size={16} style={{ stroke: 'var(--c-fg-3)' }} />
                <input placeholder="Marca, modelo, patente…" value={search}
                  onChange={e => setSearch(e.target.value)} />
              </div>
            </div>
            <div>
              <label>Estado</label>
              <select className="input" value={estado} onChange={e => setEstado(e.target.value)}>
                {ESTADOS.map(e => <option key={e} value={e}>{e === 'todos' ? 'Todos' : e.replace(/_/g, ' ')}</option>)}
              </select>
            </div>
            <div>
              <label>Tipo</label>
              <select className="input" value={tipo} onChange={e => setTipo(e.target.value)}>
                {TIPOS.map(t => <option key={t} value={t}>{t === 'todos' ? 'Todos' : t.replace(/_/g, ' ')}</option>)}
              </select>
            </div>
            <div>
              <label>Vista</label>
              <div className="seg" style={{ marginTop: 0 }}>
                <button className={view === 'cards' ? 'on' : ''} onClick={() => setView('cards')}>
                  <Icon name="grid" size={13} /> Tarjetas
                </button>
                <button className={view === 'list' ? 'on' : ''} onClick={() => setView('list')}>
                  <Icon name="list" size={13} /> Lista
                </button>
              </div>
            </div>
            <div style={{ alignSelf: 'flex-end' }}>
              <button className={`btn ${numFiltrosActivos > 0 ? 'primary' : 'ghost'}`}
                onClick={() => setFiltrosExp(x => !x)}>
                <Icon name="search" size={13} />
                Filtros{numFiltrosActivos > 0 ? ` (${numFiltrosActivos})` : ''}
              </button>
            </div>
          </div>

          {filtrosExp && (
            <div className="filter-row" style={{ marginTop: 10, paddingTop: 10, borderTop: '1px solid var(--c-border)' }}>
              <div>
                <label>Año desde</label>
                <input className="input" type="number" placeholder="2015" value={anioMin}
                  onChange={e => setAnioMin(e.target.value)} style={{ width: 90 }} />
              </div>
              <div>
                <label>Año hasta</label>
                <input className="input" type="number" placeholder="2024" value={anioMax}
                  onChange={e => setAnioMax(e.target.value)} style={{ width: 90 }} />
              </div>
              <div>
                <label>Km máx</label>
                <input className="input" type="number" placeholder="100000" value={kmMax}
                  onChange={e => setKmMax(e.target.value)} style={{ width: 110 }} />
              </div>
              <div>
                <label>Precio USD mín</label>
                <input className="input" type="number" placeholder="5000" value={precioMin}
                  onChange={e => setPrecioMin(e.target.value)} style={{ width: 110 }} />
              </div>
              <div>
                <label>Precio USD máx</label>
                <input className="input" type="number" placeholder="50000" value={precioMax}
                  onChange={e => setPrecioMax(e.target.value)} style={{ width: 110 }} />
              </div>
              <div style={{ alignSelf: 'flex-end' }}>
                <button className="btn ghost" onClick={() => {
                  setAnioMin(''); setAnioMax(''); setKmMax(''); setPrecioMin(''); setPrecioMax('')
                }}>Limpiar</button>
              </div>
            </div>
          )}
        </div>

        {/* ── Listado ── */}
        {loading ? (
          <p style={{ color: 'var(--c-fg-2)', textAlign: 'center', padding: 40 }}>Cargando…</p>
        ) : shown.length === 0 ? (
          <div className="banner info"><Icon name="info" size={16} />No hay vehículos con esos filtros.</div>
        ) : view === 'cards' ? (
          <div className="veh-grid">
            {shown.map(v => <VehicleCard key={v.id} v={v} />)}
          </div>
        ) : (
          <div>
            {shown.map(v => (
              editId === v.id ? (
                /* ── Fila en edición ── */
                <div key={v.id} className="list-row" style={{ background: 'var(--c-bg-2)', cursor: 'default' }}
                  onClick={e => e.stopPropagation()}>
                  <div>
                    <div className="v-title">{v.marca} {v.modelo} {v.anio}{v.version ? ` · ${v.version}` : ''}</div>
                    <div className="v-meta">{v.patente || '—'}</div>
                  </div>
                  <div>
                    <select className="input" style={{ fontSize: 12 }} value={editForm.estado}
                      onChange={e => setEditForm(p => ({ ...p, estado: e.target.value }))}>
                      {ESTADOS_EDIT.map(s => <option key={s} value={s}>{s.replace(/_/g,' ')}</option>)}
                    </select>
                  </div>
                  <div style={{ display: 'flex', gap: 6 }}>
                    <input className="input" type="number" style={{ width: 100, fontSize: 12 }}
                      placeholder="km" value={editForm.km_hs}
                      onChange={e => setEditForm(p => ({ ...p, km_hs: e.target.value }))} />
                    <input className="input" type="number" style={{ width: 100, fontSize: 12 }}
                      placeholder="USD" value={editForm.precio_base}
                      onChange={e => setEditForm(p => ({ ...p, precio_base: e.target.value }))} />
                  </div>
                  <div style={{ display: 'flex', gap: 6 }}>
                    <button className="btn primary" style={{ fontSize: 12, padding: '4px 10px' }}
                      disabled={savingId === v.id} onClick={e => saveEdit(v.id, e)}>
                      {savingId === v.id ? '…' : <Icon name="check" size={13} />}
                    </button>
                    <button className="btn ghost" style={{ fontSize: 12, padding: '4px 10px' }}
                      onClick={cancelEdit}>
                      <Icon name="close" size={13} />
                    </button>
                  </div>
                </div>
              ) : (
                /* ── Fila normal ── */
                <div key={v.id} className="list-row" onClick={() => navigate(`/vehiculo/${v.id}`)}>
                  <div>
                    <div className="v-title">{v.marca} {v.modelo} {v.anio}{v.version ? ` · ${v.version}` : ''}</div>
                    <div className="v-meta">{v.patente || '—'} · #{v.id} · {v.color || '—'}</div>
                  </div>
                  <div><StateBadge estado={v.estado} /></div>
                  <div className="num">{v.km_hs?.toLocaleString('es-AR') || '0'} km</div>
                  <div className="price-cell">
                    <strong>USD {v.precio_base?.toLocaleString('es-AR')}</strong>
                    <div className="ars">$ {((v.precio_base || 0) * TC).toLocaleString('es-AR')} ARS</div>
                  </div>
                  <div style={{ display: 'flex', gap: 6, justifySelf: 'end' }}>
                    <button className="btn ghost" style={{ padding: '4px 8px' }}
                      onClick={e => startEdit(v, e)} title="Edición rápida">
                      <Icon name="edit" size={14} />
                    </button>
                    <Icon name="chev-r" size={16} style={{ stroke: 'var(--c-fg-2)' }} />
                  </div>
                </div>
              )
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
