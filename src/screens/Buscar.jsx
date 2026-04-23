import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import TopBar from '../components/TopBar'
import StateBadge from '../components/StateBadge'
import Icon from '../components/Icon'
import FormField from '../components/FormField'
import { getVehiculos } from '../lib/supabase'
import { useTc } from '../hooks/useTc'
import { callAI, aiConfigured } from '../lib/api'

export default function Buscar({ onLogout }) {
  const TC       = useTc()
  const navigate = useNavigate()

  const [todos, setTodos]       = useState([])
  const [loading, setLoading]   = useState(true)

  const [filters, setFilters] = useState({
    tipo: 'todos', marca: '', anio_min: '', anio_max: '',
    km_max: '', precio_min: '', precio_max: '',
    combustible: '', transmision: '', search: '',
  })

  // IA ranking
  const [preferencias, setPreferencias] = useState('')
  const [presupuesto,  setPresupuesto]  = useState('')
  const [ranking,      setRanking]      = useState(null)
  const [rankLoading,  setRankLoading]  = useState(false)
  const [rankErr,      setRankErr]      = useState('')

  // Presupuesto WhatsApp
  const [wspVeh,    setWspVeh]    = useState(null)
  const [wspLoading, setWspLoading] = useState(false)
  const [wspTexto,  setWspTexto]  = useState('')

  useEffect(() => {
    getVehiculos({ estado: 'disponible' }).then(v => { setTodos(v); setLoading(false) })
  }, [])

  const ff = (k) => (e) => setFilters(p => ({ ...p, [k]: e.target.value }))
  function reset() {
    setFilters({ tipo: 'todos', marca: '', anio_min: '', anio_max: '', km_max: '', precio_min: '', precio_max: '', combustible: '', transmision: '', search: '' })
  }

  const resultados = todos.filter(v => {
    if (filters.tipo !== 'todos' && v.tipo !== filters.tipo) return false
    if (filters.marca && !v.marca?.toLowerCase().includes(filters.marca.toLowerCase())) return false
    if (filters.anio_min && v.anio < Number(filters.anio_min)) return false
    if (filters.anio_max && v.anio > Number(filters.anio_max)) return false
    if (filters.km_max && v.km_hs > Number(filters.km_max)) return false
    if (filters.precio_min && v.precio_base < Number(filters.precio_min)) return false
    if (filters.precio_max && v.precio_base > Number(filters.precio_max)) return false
    if (filters.combustible && v.combustible?.toLowerCase() !== filters.combustible.toLowerCase()) return false
    if (filters.transmision && v.transmision?.toLowerCase() !== filters.transmision.toLowerCase()) return false
    if (filters.search) {
      const q = filters.search.toLowerCase()
      if (!(v.marca?.toLowerCase().includes(q) || v.modelo?.toLowerCase().includes(q) || v.version?.toLowerCase().includes(q) || v.patente?.toLowerCase().includes(q))) return false
    }
    return true
  })

  const activeFilters = Object.entries(filters).filter(([, v]) => v && v !== 'todos').length
  const marcas = [...new Set(todos.map(v => v.marca).filter(Boolean))].sort()

  async function handleRanking() {
    if (!resultados.length) return
    setRankLoading(true); setRankErr(''); setRanking(null)
    try {
      const data = await callAI('/ai/ranking-vehiculos', {
        vehiculos: resultados.slice(0, 10),
        preferencias,
        presupuesto_usd: presupuesto ? Number(presupuesto) : null,
      })
      setRanking(data.ranking || [])
    } catch (e) {
      setRankErr('Error IA: ' + e.message)
    } finally { setRankLoading(false) }
  }

  async function handlePresupuestoWsp(v) {
    setWspVeh(v); setWspTexto(''); setWspLoading(true)
    try {
      const data = await callAI('/ai/presupuesto-wsp', {
        vehiculo: v,
        precio_usd: v.precio_base,
        tipo_cambio: TC,
      })
      setWspTexto(data.texto)
    } catch (e) {
      setWspTexto('Error: ' + e.message)
    } finally { setWspLoading(false) }
  }

  function copyWsp() {
    navigator.clipboard.writeText(wspTexto).catch(() => {})
  }

  // Map id → vehiculo for ranking display
  const vehById = Object.fromEntries(todos.map(v => [String(v.id), v]))

  return (
    <div>
      <TopBar onLogout={onLogout} />
      <div className="main">
        <div className="page-head">
          <div>
            <h1 className="page-title">Buscar para cliente</h1>
            <p className="page-caption">Encontrá el vehículo ideal con filtros y ranking IA</p>
          </div>
          {activeFilters > 0 && (
            <button className="btn secondary" onClick={reset}>
              <Icon name="x" size={14} /> Limpiar filtros ({activeFilters})
            </button>
          )}
        </div>

        {/* Filtros */}
        <div className="card" style={{ marginBottom: 16 }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 12 }}>
            <FormField label="Buscar texto">
              <input className="input" placeholder="Marca, modelo, patente…" value={filters.search} onChange={ff('search')} />
            </FormField>
            <FormField label="Tipo">
              <select className="input" value={filters.tipo} onChange={ff('tipo')}>
                <option value="todos">Todos</option>
                <option value="auto">Auto</option>
                <option value="moto">Moto</option>
                <option value="cuatriciclo">Cuatriciclo</option>
                <option value="moto_de_agua">Moto de agua</option>
              </select>
            </FormField>
            <FormField label="Marca">
              <select className="input" value={filters.marca} onChange={ff('marca')}>
                <option value="">Todas las marcas</option>
                {marcas.map(m => <option key={m} value={m}>{m}</option>)}
              </select>
            </FormField>
            <FormField label="Año desde">
              <input className="input" type="number" placeholder="2015" value={filters.anio_min} onChange={ff('anio_min')} min={1990} max={2030} />
            </FormField>
            <FormField label="Año hasta">
              <input className="input" type="number" placeholder={new Date().getFullYear()} value={filters.anio_max} onChange={ff('anio_max')} min={1990} max={2030} />
            </FormField>
            <FormField label="Km máximo">
              <input className="input" type="number" placeholder="150000" value={filters.km_max} onChange={ff('km_max')} min={0} />
            </FormField>
            <FormField label="Precio mín (USD)">
              <input className="input" type="number" placeholder="0" value={filters.precio_min} onChange={ff('precio_min')} min={0} />
            </FormField>
            <FormField label="Precio máx (USD)">
              <input className="input" type="number" placeholder="Sin límite" value={filters.precio_max} onChange={ff('precio_max')} min={0} />
            </FormField>
            <FormField label="Combustible">
              <select className="input" value={filters.combustible} onChange={ff('combustible')}>
                <option value="">Cualquiera</option>
                {['Nafta', 'Diesel', 'GNC', 'Nafta/GNC', 'Híbrido', 'Eléctrico'].map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </FormField>
            <FormField label="Transmisión">
              <select className="input" value={filters.transmision} onChange={ff('transmision')}>
                <option value="">Cualquiera</option>
                {['Manual', 'Automática', 'CVT', 'Secuencial'].map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </FormField>
          </div>
        </div>

        {/* Panel IA Ranking */}
        {aiConfigured() && (
          <div className="card" style={{ marginBottom: 20 }}>
            <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 10, display: 'flex', alignItems: 'center', gap: 6 }}>
              <Icon name="star" size={14} style={{ stroke: 'var(--c-accent)' }} />
              Ranking IA para el cliente
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 160px', gap: 10, marginBottom: 10 }}>
              <FormField label="Preferencias del cliente (texto libre)">
                <input className="input" placeholder="Ej: familia de 5 personas, quiero bajo mantenimiento, presupuesto acotado…"
                  value={preferencias} onChange={e => setPreferencias(e.target.value)} />
              </FormField>
              <FormField label="Presupuesto máx (USD)">
                <input className="input" type="number" placeholder="Sin límite" value={presupuesto} onChange={e => setPresupuesto(e.target.value)} />
              </FormField>
            </div>
            <button className="btn primary" style={{ fontSize: 13 }}
              disabled={rankLoading || !resultados.length}
              onClick={handleRanking}>
              <Icon name="star" size={14} />
              {rankLoading ? 'Analizando…' : `Rankear los ${Math.min(resultados.length, 10)} resultados`}
            </button>
            {rankErr && <div className="banner warning" style={{ marginTop: 10 }}><Icon name="alert" size={14} />{rankErr}</div>}

            {ranking && ranking.length > 0 && (
              <div style={{ marginTop: 14, display: 'flex', flexDirection: 'column', gap: 10 }}>
                <div style={{ fontSize: 12, color: 'var(--c-fg-3)', fontWeight: 600 }}>TOP 3 recomendados</div>
                {ranking.map((r, idx) => {
                  const v = vehById[String(r.id)]
                  if (!v) return null
                  return (
                    <div key={r.id} style={{ background: 'var(--c-bg-2)', borderRadius: 'var(--r)', padding: 14, borderLeft: `3px solid ${idx === 0 ? '#f59e0b' : idx === 1 ? '#94a3b8' : '#cd7c2f'}` }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                        <div style={{ fontSize: 20, fontWeight: 800, color: idx === 0 ? '#f59e0b' : 'var(--c-fg-2)' }}>#{idx + 1}</div>
                        <div style={{ flex: 1 }}>
                          <div className="v-title">{v.marca} {v.modelo} {v.anio}{v.version ? ` · ${v.version}` : ''}</div>
                          <div className="v-meta">{v.patente || '—'} · USD {v.precio_base?.toLocaleString('es-AR')} · {v.km_hs?.toLocaleString('es-AR') || '0'} km</div>
                        </div>
                        <div style={{ textAlign: 'center' }}>
                          <div style={{ fontSize: 22, fontWeight: 800, color: 'var(--c-accent)' }}>{r.score}</div>
                          <div style={{ fontSize: 10, color: 'var(--c-fg-3)' }}>/10</div>
                        </div>
                      </div>
                      <div style={{ fontSize: 13, marginBottom: 6, color: 'var(--c-fg)' }}>{r.por_que}</div>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 12 }}>
                        <div style={{ background: 'var(--c-bg)', borderRadius: 'var(--r)', padding: '6px 10px' }}>
                          <div style={{ color: '#22c55e', fontWeight: 600, marginBottom: 2 }}>✓ {r.punto_fuerte}</div>
                        </div>
                        <div style={{ background: 'var(--c-bg)', borderRadius: 'var(--r)', padding: '6px 10px' }}>
                          <div style={{ color: 'var(--c-fg-2)', marginBottom: 2 }}>△ {r.punto_debil}</div>
                        </div>
                      </div>
                      <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
                        <button className="btn primary" style={{ fontSize: 12 }} onClick={() => navigate(`/vehiculo/${v.id}`)}>
                          <Icon name="eye" size={13} /> Ver detalle
                        </button>
                        <button className="btn secondary" style={{ fontSize: 12 }} onClick={() => handlePresupuestoWsp(v)}>
                          <Icon name="message" size={13} /> Presupuesto WSP
                        </button>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        )}

        {/* Presupuesto WhatsApp modal */}
        {wspVeh && (
          <div className="modal-overlay" onClick={() => { setWspVeh(null); setWspTexto('') }}>
            <div className="modal" onClick={e => e.stopPropagation()} style={{ maxWidth: 480 }}>
              <div className="modal-head">
                <h3>Presupuesto WhatsApp</h3>
                <button className="btn ghost" onClick={() => { setWspVeh(null); setWspTexto('') }}><Icon name="close" size={16} /></button>
              </div>
              <div style={{ padding: '0 20px 20px' }}>
                <div style={{ fontSize: 13, color: 'var(--c-fg-2)', marginBottom: 10 }}>
                  {wspVeh.marca} {wspVeh.modelo} {wspVeh.anio} · USD {wspVeh.precio_base?.toLocaleString('es-AR')}
                </div>
                {wspLoading ? (
                  <p style={{ color: 'var(--c-fg-2)' }}>Generando mensaje…</p>
                ) : (
                  <>
                    <textarea className="input" rows={10} readOnly value={wspTexto}
                      style={{ width: '100%', resize: 'vertical', fontSize: 13, fontFamily: 'inherit' }} />
                    <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
                      <button className="btn primary" onClick={copyWsp}>
                        <Icon name="clipboard" size={14} /> Copiar
                      </button>
                      {wspVeh.whatsapp && (
                        <a href={`https://wa.me/${wspVeh.whatsapp?.replace(/\D/g, '')}?text=${encodeURIComponent(wspTexto)}`}
                          target="_blank" rel="noreferrer" className="btn secondary" style={{ fontSize: 13 }}>
                          Abrir en WA
                        </a>
                      )}
                    </div>
                  </>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Resultados */}
        {loading ? <p style={{ color: 'var(--c-fg-2)' }}>Cargando stock…</p> : (
          <>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
              <p style={{ color: 'var(--c-fg-2)', margin: 0, fontSize: 14 }}>
                <strong style={{ color: 'var(--c-fg)' }}>{resultados.length}</strong> vehículo{resultados.length !== 1 ? 's' : ''} encontrado{resultados.length !== 1 ? 's' : ''}
                {todos.length !== resultados.length && <> de {todos.length} disponibles</>}
              </p>
            </div>

            {resultados.length === 0 ? (
              <div className="banner info">
                <Icon name="info" size={16} />
                Sin resultados con los filtros actuales.
                {activeFilters > 0 && <button className="btn ghost" style={{ marginLeft: 8, padding: '2px 8px', fontSize: 12 }} onClick={reset}>Limpiar filtros</button>}
              </div>
            ) : (
              resultados.map(v => (
                <div key={v.id} className="list-row" style={{ cursor: 'pointer' }} onClick={() => navigate(`/vehiculo/${v.id}`)}>
                  <div>
                    <div className="v-title">{v.marca} {v.modelo} {v.anio}{v.version ? ` · ${v.version}` : ''}</div>
                    <div className="v-meta">
                      {v.patente || '—'} · #{v.id}
                      {v.combustible ? ` · ${v.combustible}` : ''}
                      {v.transmision ? ` · ${v.transmision}` : ''}
                    </div>
                  </div>
                  <StateBadge estado={v.estado} />
                  <div className="num">{v.km_hs?.toLocaleString('es-AR') || '0'} km</div>
                  <div style={{ textAlign: 'right' }}>
                    <div className="price-cell"><strong>USD {v.precio_base?.toLocaleString('es-AR') || '—'}</strong></div>
                    {v.precio_base && TC > 0 && (
                      <div style={{ fontSize: 12, color: 'var(--c-fg-2)' }}>$ {(v.precio_base * TC).toLocaleString('es-AR', { maximumFractionDigits: 0 })}</div>
                    )}
                  </div>
                  <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                    {aiConfigured() && (
                      <button className="btn ghost" style={{ padding: '4px 8px', fontSize: 12 }}
                        onClick={e => { e.stopPropagation(); handlePresupuestoWsp(v) }} title="Presupuesto WSP">
                        <Icon name="message" size={14} />
                      </button>
                    )}
                    <Icon name="chev-r" size={16} style={{ stroke: 'var(--c-fg-2)' }} />
                  </div>
                </div>
              ))
            )}
          </>
        )}
      </div>
    </div>
  )
}
