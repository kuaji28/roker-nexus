import { useEffect, useState } from 'react'
import TopBar from '../components/TopBar'
import Icon from '../components/Icon'
import { getStats, getVentas, getVendedores } from '../lib/supabase'

export default function Gerente({ onLogout }) {
  const [stats, setStats]         = useState(null)
  const [ventas, setVentas]       = useState([])
  const [vendedores, setVendedores] = useState([])

  useEffect(() => {
    getStats().then(setStats)
    getVentas().then(setVentas)
    getVendedores().then(setVendedores)
  }, [])

  const ranking = vendedores.map(vend => {
    const vv = ventas.filter(v => v.vendedor_id === vend.id)
    return { ...vend, total: vv.length, volumen: vv.reduce((s, v) => s + (Number(v.precio_final) || 0), 0) }
  }).filter(v => v.total > 0).sort((a, b) => b.total - a.total)

  const recentVentas = ventas.slice(0, 8)

  return (
    <div>
      <TopBar onLogout={onLogout} />
      <div className="main">
        <div className="page-head">
          <div>
            <h1 className="page-title">Dashboard Gerente</h1>
            <p className="page-caption">Vista ejecutiva del negocio</p>
          </div>
        </div>

        <h2 className="section-title">Estado del stock</h2>
        <div className="metric-grid">
          <div className="mc" style={{ cursor: 'default' }}>
            <div className="ribbon g" />
            <div className="lbl"><Icon name="check" size={14} />Disponibles</div>
            <div className="val g">{stats?.disponible ?? '—'}</div>
          </div>
          <div className="mc" style={{ cursor: 'default' }}>
            <div className="ribbon o" />
            <div className="lbl">Señados</div>
            <div className="val o">{stats?.seniado ?? '—'}</div>
          </div>
          <div className="mc" style={{ cursor: 'default' }}>
            <div className="ribbon b" />
            <div className="lbl"><Icon name="eye" size={14} />En revisión</div>
            <div className="val b">{stats?.en_revision ?? '—'}</div>
          </div>
          <div className="mc" style={{ cursor: 'default' }}>
            <div className="ribbon r" />
            <div className="lbl">Vendidos</div>
            <div className="val r">{stats?.vendido ?? '—'}</div>
          </div>
        </div>

        {ranking.length > 0 && (
          <>
            <h2 className="section-title" style={{ marginTop: 28 }}>Ranking vendedores</h2>
            <table className="rank">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Vendedor</th>
                  <th className="num">Ventas</th>
                  <th className="num">Volumen USD</th>
                  <th style={{ width: 140 }}>Progreso</th>
                </tr>
              </thead>
              <tbody>
                {ranking.map((v, i) => (
                  <tr key={v.id}>
                    <td><strong>{i + 1}</strong></td>
                    <td><strong>{v.nombre}</strong></td>
                    <td className="num">{v.total}</td>
                    <td className="num">USD {v.volumen.toLocaleString('es-AR')}</td>
                    <td>
                      <div className="bar-wrap">
                        <div className="bar-fill" style={{ width: `${(v.total / ranking[0].total) * 100}%` }} />
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}

        {recentVentas.length > 0 && (
          <>
            <h2 className="section-title" style={{ marginTop: 28 }}>Últimas ventas</h2>
            <table className="rank">
              <thead>
                <tr>
                  <th>Vehículo</th>
                  <th>Comprador</th>
                  <th>Vendedor</th>
                  <th className="num">Precio</th>
                  <th>Fecha</th>
                </tr>
              </thead>
              <tbody>
                {recentVentas.map(v => (
                  <tr key={v.id}>
                    <td><strong>{v.vehiculos?.marca} {v.vehiculos?.modelo} {v.vehiculos?.anio}</strong></td>
                    <td>{v.comprador_nombre || '—'}</td>
                    <td>{v.vendedores?.nombre || '—'}</td>
                    <td className="num">{v.moneda_precio || 'USD'} {Number(v.precio_final).toLocaleString('es-AR')}</td>
                    <td style={{ color: 'var(--c-fg-2)', fontSize: 12 }}>{v.fecha_venta}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}

        {ranking.length === 0 && recentVentas.length === 0 && (
          <div className="banner info" style={{ marginTop: 16 }}>
            <Icon name="info" size={16} />No hay ventas registradas todavía.
          </div>
        )}
      </div>
    </div>
  )
}
