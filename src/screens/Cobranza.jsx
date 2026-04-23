import { useEffect, useState } from 'react'
import TopBar from '../components/TopBar'
import Icon from '../components/Icon'
import { getFinanciamientos, getCuotasVencidas } from '../lib/supabase'

export default function Cobranza({ onLogout }) {
  const [finan, setFinan]     = useState([])
  const [cuotas, setCuotas]   = useState([])
  const [tab, setTab]         = useState('vencidas')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([getFinanciamientos(), getCuotasVencidas()]).then(([f, c]) => {
      setFinan(f); setCuotas(c); setLoading(false)
    })
  }, [])

  const totalVencido = cuotas.reduce((s, c) => s + (Number(c.monto) || 0), 0)

  return (
    <div>
      <TopBar onLogout={onLogout} />
      <div className="main">
        <div className="page-head">
          <div>
            <h1 className="page-title">Cobranza</h1>
            <p className="page-caption">Financiamientos y cuotas</p>
          </div>
          {cuotas.length > 0 && (
            <div className="banner warning" style={{ margin: 0 }}>
              <Icon name="alert" size={16} />
              {cuotas.length} cuota{cuotas.length > 1 ? 's' : ''} vencida{cuotas.length > 1 ? 's' : ''}
            </div>
          )}
        </div>

        <div className="tabs">
          {[['vencidas','alert','Vencidas'], ['todos','briefcase','Todos']].map(([k, ic, l]) => (
            <button key={k} className={tab === k ? 'on' : ''} onClick={() => setTab(k)}>
              <Icon name={ic} size={13} />{l}
              {k === 'vencidas' && cuotas.length > 0 && (
                <span style={{ marginLeft: 4, fontSize: 11, background: 'var(--c-danger)', color: '#fff', borderRadius: 999, padding: '1px 6px' }}>
                  {cuotas.length}
                </span>
              )}
            </button>
          ))}
        </div>

        {loading ? (
          <p style={{ color: 'var(--c-fg-2)' }}>Cargando…</p>
        ) : tab === 'vencidas' ? (
          cuotas.length === 0
            ? <div className="banner success"><Icon name="check" size={16} />No hay cuotas vencidas.</div>
            : (
              <>
                <div className="banner warning">
                  <Icon name="cash" size={16} />
                  Total vencido: <strong style={{ marginLeft: 4 }}>$ {totalVencido.toLocaleString('es-AR')}</strong>
                </div>
                <table className="rank">
                  <thead>
                    <tr>
                      <th>Deudor</th>
                      <th>Vehículo</th>
                      <th className="num">Monto</th>
                      <th>Vencimiento</th>
                      <th>Estado</th>
                    </tr>
                  </thead>
                  <tbody>
                    {cuotas.map(c => (
                      <tr key={c.id}>
                        <td><strong>{c.financiamientos?.deudor_nombre || '—'}</strong></td>
                        <td style={{ color: 'var(--c-fg-2)', fontSize: 12 }}>
                          {c.financiamientos?.vehiculos?.marca} {c.financiamientos?.vehiculos?.modelo}
                        </td>
                        <td className="num">$ {Number(c.monto || 0).toLocaleString('es-AR')}</td>
                        <td style={{ color: 'var(--c-danger)', fontSize: 12 }}>{c.fecha_vencimiento}</td>
                        <td><span className="badge danger"><span className="cdot" /> Vencida</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </>
            )
        ) : (
          finan.length === 0
            ? <div className="banner info"><Icon name="info" size={16} />No hay financiamientos registrados.</div>
            : (
              <table className="rank">
                <thead>
                  <tr>
                    <th>Deudor</th>
                    <th>Vehículo</th>
                    <th className="num">Total</th>
                    <th>Cuotas</th>
                    <th>Estado</th>
                  </tr>
                </thead>
                <tbody>
                  {finan.map(fn => (
                    <tr key={fn.id}>
                      <td><strong>{fn.deudor_nombre || '—'}</strong></td>
                      <td style={{ color: 'var(--c-fg-2)', fontSize: 12 }}>
                        {fn.vehiculos?.marca} {fn.vehiculos?.modelo} {fn.vehiculos?.anio}
                      </td>
                      <td className="num">$ {Number(fn.monto_total || 0).toLocaleString('es-AR')}</td>
                      <td style={{ color: 'var(--c-fg-2)', fontSize: 12 }}>{fn.cantidad_cuotas || '—'}</td>
                      <td>
                        <span className={`badge ${fn.estado === 'activo' ? 'success' : fn.estado === 'vencido' ? 'danger' : 'neutral'}`}>
                          <span className="cdot" /> {fn.estado || 'activo'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )
        )}
      </div>
    </div>
  )
}
