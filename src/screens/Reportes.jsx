import { useEffect, useState } from 'react'
import TopBar from '../components/TopBar'
import MetricCard from '../components/MetricCard'
import Icon from '../components/Icon'
import { getReportes } from '../lib/supabase'

function BarChart({ bars }) {
  const maxCount = Math.max(...bars.map(b => b.count), 1)
  return (
    <div style={{ display: 'flex', alignItems: 'flex-end', gap: 8, height: 120, padding: '0 4px' }}>
      {bars.map((b, i) => (
        <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
          <span style={{ fontSize: 10, color: 'var(--c-fg-2)', fontFamily: 'var(--mono)' }}>{b.count}</span>
          <div style={{ width: '100%', background: 'var(--c-card-2)', borderRadius: 4, overflow: 'hidden', height: 80 }}>
            <div style={{
              width: '100%',
              height: `${(b.count / maxCount) * 100}%`,
              background: i === bars.length - 1 ? 'var(--c-success)' : 'var(--c-info)',
              borderRadius: '4px 4px 0 0',
              marginTop: `${100 - (b.count / maxCount) * 100}%`,
              transition: 'height .3s ease',
            }} />
          </div>
          <span style={{ fontSize: 10, color: 'var(--c-fg-3)', textTransform: 'uppercase' }}>{b.label}</span>
        </div>
      ))}
    </div>
  )
}

export default function Reportes({ onLogout }) {
  const [data, setData]       = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getReportes().then(d => { setData(d); setLoading(false) })
  }, [])

  return (
    <div>
      <TopBar onLogout={onLogout} />
      <div className="main">
        <div className="page-head">
          <div>
            <h1 className="page-title">Reportes</h1>
            <p className="page-caption">{new Date().toLocaleDateString('es-AR', { month: 'long', year: 'numeric' })}</p>
          </div>
        </div>

        {loading ? (
          <p style={{ color: 'var(--c-fg-2)' }}>Cargando…</p>
        ) : (
          <>
            <h2 className="section-title">Resumen del mes</h2>
            <div className="metric-grid">
              <MetricCard label="Ventas del mes"    icon="cash"  value={data.ventasMes}   tone="g" sub="vehículos vendidos" />
              <MetricCard label="Ingreso USD"        icon="chart" value={`USD ${data.ingresoUSD.toLocaleString('es-AR')}`} tone="g" />
              <MetricCard label="Stock disponible"   icon="car"   value={`USD ${data.stockUSD.toLocaleString('es-AR')}`}   tone="b" sub="valor en stock" />
              <MetricCard label="Ingresos al stock"  icon="plus"  value={data.ingresosMes} sub="este mes" />
              <MetricCard label="Leads nuevos"       icon="users" value={data.leadsNuevos} tone="o" />
            </div>

            <h2 className="section-title" style={{ marginTop: 28 }}>Ventas últimos 6 meses</h2>
            <div className="card">
              <BarChart bars={data.bars} />
              <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 12 }}>
                {data.bars.map((b, i) => (
                  <div key={i} style={{ flex: 1, textAlign: 'center', fontSize: 10, color: 'var(--c-fg-3)', fontFamily: 'var(--mono)' }}>
                    {b.total > 0 && `USD ${b.total.toLocaleString('es-AR')}`}
                  </div>
                ))}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
