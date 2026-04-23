import { useEffect, useState } from 'react'
import TopBar from '../components/TopBar'
import Icon from '../components/Icon'
import { getFinanciamientos, getCuotasVencidas, getCuotasProximas, pagarCuotaConMetadata } from '../lib/supabase'
import { useTc } from '../hooks/useTc'

const FORMAS_COBRO = ['Efectivo', 'Transferencia', 'Efectivo + Transferencia']
const MONEDAS = ['ARS', 'USD']

const URGENCIA = (fechaVenc) => {
  const dias = Math.ceil((new Date(fechaVenc) - new Date()) / 86400000)
  if (dias < 0)   return { label: 'Vencida',       cls: 'danger'  }
  if (dias <= 5)  return { label: `${dias}d`,       cls: 'danger'  }
  if (dias <= 15) return { label: `${dias}d`,       cls: 'warning' }
  return           { label: `${dias}d`,             cls: 'success' }
}

const EMPTY_PAGO = { monto_pagado: '', forma_cobro: 'Efectivo', moneda_cobro: 'ARS', tc_cobro: '', notas_cobro: '' }

export default function Cobranza({ onLogout }) {
  const TC = useTc()
  const [finan, setFinan]         = useState([])
  const [vencidas, setVencidas]   = useState([])
  const [proximas, setProximas]   = useState([])
  const [tab, setTab]             = useState('vencidas')
  const [loading, setLoading]     = useState(true)
  const [filtroEstado, setFiltroEstado] = useState('todos')
  const [dias, setDias]           = useState(30)

  // Modal pago
  const [modalCuota, setModalCuota] = useState(null)
  const [pago, setPago]           = useState(EMPTY_PAGO)
  const [pagando, setPagando]     = useState(false)
  const [pagoErr, setPagoErr]     = useState('')

  async function load() {
    const [f, v, p] = await Promise.all([
      getFinanciamientos(),
      getCuotasVencidas(),
      getCuotasProximas(dias),
    ])
    setFinan(f); setVencidas(v); setProximas(p); setLoading(false)
  }

  useEffect(() => { load() }, [dias])

  function abrirModal(cuota) {
    setModalCuota(cuota)
    setPago({ ...EMPTY_PAGO, monto_pagado: cuota.monto || '', tc_cobro: TC || '' })
    setPagoErr('')
  }

  async function confirmarPago() {
    if (!pago.forma_cobro) { setPagoErr('Seleccioná forma de cobro'); return }
    setPagando(true)
    try {
      await pagarCuotaConMetadata(modalCuota.id, {
        monto_pagado:  pago.monto_pagado  ? Number(pago.monto_pagado)  : undefined,
        forma_cobro:   pago.forma_cobro   || undefined,
        moneda_cobro:  pago.moneda_cobro  || undefined,
        tc_cobro:      pago.tc_cobro      ? Number(pago.tc_cobro)      : undefined,
        notas_cobro:   pago.notas_cobro   || undefined,
      })
      setModalCuota(null)
      await load()
    } catch (e) {
      setPagoErr(e.message || 'Error al registrar pago')
    } finally {
      setPagando(false)
    }
  }

  const totalVencido  = vencidas.reduce((s, c) => s + (Number(c.monto) || 0), 0)
  const totalProximo  = proximas.reduce((s, c) => s + (Number(c.monto) || 0), 0)
  const finanFil = filtroEstado === 'todos' ? finan : finan.filter(fn => fn.estado === filtroEstado)

  const CuotaRow = ({ c, badge }) => (
    <div className="list-row" style={{ cursor: 'default' }}>
      <div>
        <div className="v-title">{c.financiamientos?.deudor_nombre || '—'}</div>
        <div className="v-meta">
          {c.financiamientos?.vehiculos?.marca} {c.financiamientos?.vehiculos?.modelo}
          {c.numero_cuota && <> · Cuota #{c.numero_cuota}</>}
        </div>
      </div>
      <div style={{ color: 'var(--c-fg-2)', fontSize: 12 }}>Vence: {c.fecha_vencimiento}</div>
      <div className="price-cell">
        <strong>$ {Number(c.monto || 0).toLocaleString('es-AR')}</strong>
      </div>
      <div>
        <span className={`badge ${badge.cls}`}><span className="cdot" /> {badge.label}</span>
      </div>
      <button
        className="btn primary"
        style={{ fontSize: 12, padding: '4px 12px', whiteSpace: 'nowrap' }}
        onClick={() => abrirModal(c)}
      >
        <Icon name="check" size={13} /> Marcar pagada
      </button>
    </div>
  )

  return (
    <div>
      <TopBar onLogout={onLogout} />
      <div className="main">
        <div className="page-head">
          <div>
            <h1 className="page-title">Cobranza</h1>
            <p className="page-caption">Financiamientos y cuotas</p>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            {vencidas.length > 0 && (
              <div className="banner warning" style={{ margin: 0 }}>
                <Icon name="alert" size={16} />
                {vencidas.length} vencida{vencidas.length > 1 ? 's' : ''} · $ {totalVencido.toLocaleString('es-AR')}
              </div>
            )}
            {proximas.length > 0 && (
              <div className="banner info" style={{ margin: 0 }}>
                <Icon name="cash" size={16} />
                {proximas.length} próxima{proximas.length > 1 ? 's' : ''} · $ {totalProximo.toLocaleString('es-AR')}
              </div>
            )}
          </div>
        </div>

        <div className="tabs">
          {[
            ['vencidas', 'alert',     vencidas.length > 0 ? `Vencidas (${vencidas.length})` : 'Vencidas'],
            ['proximas', 'cash',      proximas.length > 0 ? `Próximas (${proximas.length})` : 'Próximas'],
            ['todos',    'briefcase', 'Financiamientos'],
          ].map(([k, ic, l]) => (
            <button key={k} className={tab === k ? 'on' : ''} onClick={() => setTab(k)}>
              <Icon name={ic} size={13} />{l}
            </button>
          ))}
        </div>

        {loading ? (
          <p style={{ color: 'var(--c-fg-2)' }}>Cargando…</p>
        ) : tab === 'vencidas' ? (
          vencidas.length === 0
            ? <div className="banner success"><Icon name="check" size={16} />No hay cuotas vencidas.</div>
            : vencidas.map(c => <CuotaRow key={c.id} c={c} badge={{ cls: 'danger', label: 'Vencida' }} />)

        ) : tab === 'proximas' ? (
          <div>
            <div style={{ display: 'flex', gap: 10, marginBottom: 16, alignItems: 'center' }}>
              <span style={{ color: 'var(--c-fg-2)', fontSize: 13 }}>Próximos</span>
              <select className="input" style={{ width: 100 }} value={dias} onChange={e => setDias(Number(e.target.value))}>
                {[7, 15, 30, 60].map(d => <option key={d} value={d}>{d} días</option>)}
              </select>
            </div>
            {proximas.length === 0
              ? <div className="banner success"><Icon name="check" size={16} />Sin cuotas próximas a vencer.</div>
              : proximas.map(c => <CuotaRow key={c.id} c={c} badge={URGENCIA(c.fecha_vencimiento)} />)
            }
          </div>

        ) : (
          <div>
            <div style={{ display: 'flex', gap: 10, marginBottom: 16, alignItems: 'center' }}>
              <select className="input" style={{ width: 180 }} value={filtroEstado} onChange={e => setFiltroEstado(e.target.value)}>
                <option value="todos">Todos los estados</option>
                <option value="activo">Activo</option>
                <option value="vencido">Vencido</option>
                <option value="cancelado">Cancelado</option>
                <option value="pagado">Pagado</option>
              </select>
              <span style={{ color: 'var(--c-fg-2)', fontSize: 13 }}>{finanFil.length} financiamiento{finanFil.length !== 1 ? 's' : ''}</span>
            </div>
            {finanFil.length === 0
              ? <div className="banner info"><Icon name="info" size={16} />No hay financiamientos con ese filtro.</div>
              : finanFil.map(fn => (
                <div key={fn.id} className="list-row" style={{ cursor: 'default' }}>
                  <div>
                    <div className="v-title">{fn.deudor_nombre || '—'}</div>
                    <div className="v-meta">
                      {fn.vehiculos?.marca} {fn.vehiculos?.modelo} {fn.vehiculos?.anio}
                      {fn.deudor_telefono && <> · {fn.deudor_telefono}</>}
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: 11, color: 'var(--c-fg-2)' }}>Total</div>
                    <div>$ {Number(fn.monto_total || 0).toLocaleString('es-AR')}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: 11, color: 'var(--c-fg-2)' }}>Cuotas</div>
                    <div>{fn.cantidad_cuotas || '—'}</div>
                  </div>
                  <div>
                    <span className={`badge ${fn.estado === 'activo' ? 'success' : fn.estado === 'vencido' ? 'danger' : 'neutral'}`}>
                      <span className="cdot" /> {fn.estado || 'activo'}
                    </span>
                  </div>
                </div>
              ))
            }
          </div>
        )}
      </div>

      {/* ── Modal registrar pago ── */}
      {modalCuota && (
        <div className="modal-overlay" onClick={() => setModalCuota(null)}>
          <div className="modal" onClick={e => e.stopPropagation()} style={{ maxWidth: 420 }}>
            <div className="modal-head">
              <h3>Registrar cobro</h3>
              <button className="btn ghost" onClick={() => setModalCuota(null)}><Icon name="close" size={16} /></button>
            </div>
            <div style={{ padding: '0 20px 20px', display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div style={{ background: 'var(--c-bg-2)', borderRadius: 8, padding: '10px 14px', fontSize: 13 }}>
                <strong>{modalCuota.financiamientos?.deudor_nombre}</strong>
                <span style={{ color: 'var(--c-fg-2)', marginLeft: 8 }}>
                  {modalCuota.financiamientos?.vehiculos?.marca} {modalCuota.financiamientos?.vehiculos?.modelo}
                  {modalCuota.numero_cuota && ` · Cuota #${modalCuota.numero_cuota}`}
                </span>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                <label style={{ fontSize: 12, color: 'var(--c-fg-2)' }}>
                  Monto cobrado
                  <input className="input" style={{ marginTop: 4 }} type="number" value={pago.monto_pagado}
                    onChange={e => setPago(p => ({ ...p, monto_pagado: e.target.value }))} />
                </label>
                <label style={{ fontSize: 12, color: 'var(--c-fg-2)' }}>
                  Moneda
                  <select className="input" style={{ marginTop: 4 }} value={pago.moneda_cobro}
                    onChange={e => setPago(p => ({ ...p, moneda_cobro: e.target.value }))}>
                    {MONEDAS.map(m => <option key={m}>{m}</option>)}
                  </select>
                </label>
                <label style={{ fontSize: 12, color: 'var(--c-fg-2)', gridColumn: '1 / -1' }}>
                  Forma de cobro
                  <select className="input" style={{ marginTop: 4 }} value={pago.forma_cobro}
                    onChange={e => setPago(p => ({ ...p, forma_cobro: e.target.value }))}>
                    {FORMAS_COBRO.map(f => <option key={f}>{f}</option>)}
                  </select>
                </label>
                {pago.moneda_cobro === 'USD' && (
                  <label style={{ fontSize: 12, color: 'var(--c-fg-2)', gridColumn: '1 / -1' }}>
                    TC aplicado
                    <input className="input" style={{ marginTop: 4 }} type="number" value={pago.tc_cobro}
                      onChange={e => setPago(p => ({ ...p, tc_cobro: e.target.value }))} />
                  </label>
                )}
                <label style={{ fontSize: 12, color: 'var(--c-fg-2)', gridColumn: '1 / -1' }}>
                  Notas (opcional)
                  <input className="input" style={{ marginTop: 4 }} value={pago.notas_cobro}
                    onChange={e => setPago(p => ({ ...p, notas_cobro: e.target.value }))} />
                </label>
              </div>
              {pagoErr && <div className="banner danger"><Icon name="alert" size={14} />{pagoErr}</div>}
              <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
                <button className="btn ghost" onClick={() => setModalCuota(null)}>Cancelar</button>
                <button className="btn primary" disabled={pagando} onClick={confirmarPago}>
                  {pagando ? 'Guardando…' : <><Icon name="check" size={14} /> Confirmar pago</>}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
