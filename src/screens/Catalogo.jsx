import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import TopBar from '../components/TopBar'
import VehicleCard from '../components/VehicleCard'
import StateBadge from '../components/StateBadge'
import Icon from '../components/Icon'
import { getVehiculos } from '../lib/supabase'
import { useTc } from '../hooks/useTc'

const ESTADOS = ['todos', 'disponible', 'señado', 'en_revision', 'en_preparacion', 'vendido']
const TIPOS   = ['todos', 'auto', 'moto', 'cuatriciclo', 'moto_de_agua']

export default function Catalogo({ onLogout }) {
  const navigate = useNavigate()
  const TC = useTc()
  const [params] = useSearchParams()
  const [vehiculos, setVehiculos] = useState([])
  const [loading, setLoading]   = useState(true)
  const [view, setView]         = useState('cards')
  const [search, setSearch]     = useState(params.get('search') || '')
  const [estado, setEstado]     = useState(params.get('estado') || 'todos')
  const [tipo, setTipo]         = useState('todos')

  useEffect(() => {
    setLoading(true)
    getVehiculos({ estado, tipo, search }).then(data => {
      setVehiculos(data)
      setLoading(false)
    })
  }, [estado, tipo, search])

  return (
    <div>
      <TopBar placeholder="Marca, modelo, patente…" onLogout={onLogout} />
      <div className="main">
        <div className="page-head">
          <div>
            <h1 className="page-title">Catálogo</h1>
            <p className="page-caption">{vehiculos.length} vehículo(s)</p>
          </div>
          <div style={{ flex: 1 }} />
          <button className="btn primary" onClick={() => navigate('/ingreso')}>
            <Icon name="plus" size={14} />
            Ingresar vehículo
          </button>
        </div>

        {/* Filter bar */}
        <div className="filter-card">
          <div className="filter-row">
            <div>
              <label>Buscar</label>
              <div className="search-field" style={{ background: 'var(--c-bg)' }}>
                <Icon name="search" size={16} style={{ stroke: 'var(--c-fg-3)' }} />
                <input
                  placeholder="Marca, modelo, patente…"
                  value={search}
                  onChange={e => setSearch(e.target.value)}
                />
              </div>
            </div>
            <div>
              <label>Estado</label>
              <select className="input" value={estado} onChange={e => setEstado(e.target.value)}>
                {ESTADOS.map(e => <option key={e} value={e}>{e === 'todos' ? 'Todos' : e.replace('_', ' ')}</option>)}
              </select>
            </div>
            <div>
              <label>Tipo</label>
              <select className="input" value={tipo} onChange={e => setTipo(e.target.value)}>
                {TIPOS.map(t => <option key={t} value={t}>{t === 'todos' ? 'Todos' : t.replace('_', ' ')}</option>)}
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
          </div>
        </div>

        {loading ? (
          <p style={{ color: 'var(--c-fg-2)', textAlign: 'center', padding: 40 }}>Cargando…</p>
        ) : vehiculos.length === 0 ? (
          <div className="banner info"><Icon name="info" size={16} />No hay vehículos con esos filtros.</div>
        ) : view === 'cards' ? (
          <div className="veh-grid">
            {vehiculos.map(v => <VehicleCard key={v.id} v={v} />)}
          </div>
        ) : (
          <div>
            {vehiculos.map(v => (
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
                <Icon name="chev-r" size={16} style={{ stroke: 'var(--c-fg-2)', justifySelf: 'end' }} />
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
