import { useEffect, useState } from 'react'
import TopBar from '../components/TopBar'
import StateBadge from '../components/StateBadge'
import Icon from '../components/Icon'
import FormField from '../components/FormField'
import { getVehiculos, getVendedores, createVenta } from '../lib/supabase'

const FORMAS = ['Efectivo', 'Transferencia', 'Efectivo + Transferencia', 'Financiación', 'Parte de pago']

export default function Ventas({ onLogout }) {
  const [step, setStep]       = useState(1)
  const [vehiculos, setVehiculos] = useState([])
  const [vendedores, setVendedores] = useState([])
  const [selected, setSelected] = useState(null)
  const [saving, setSaving]   = useState(false)
  const [done, setDone]       = useState(null)
  const [error, setError]     = useState('')
  const [buyer, setBuyer]     = useState({
    comprador_nombre: '', comprador_dni: '', comprador_telefono: '',
    precio_final: '', moneda_precio: 'USD', forma_pago: 'Efectivo',
    vendedor_id: '', notas: '',
  })

  useEffect(() => {
    getVehiculos({ estado: 'disponible' }).then(setVehiculos)
    getVendedores().then(setVendedores)
  }, [])

  const f = (k) => (e) => setBuyer(p => ({ ...p, [k]: e.target.value }))

  async function confirm() {
    if (!buyer.comprador_nombre || !buyer.precio_final) {
      setError('Completá nombre del comprador y precio final.')
      return
    }
    setSaving(true)
    setError('')
    try {
      const v = await createVenta({
        vehiculo_id: selected.id,
        vendedor_id: buyer.vendedor_id || null,
        precio_final: Number(buyer.precio_final),
        moneda_precio: buyer.moneda_precio,
        comprador_nombre: buyer.comprador_nombre,
        comprador_dni: buyer.comprador_dni || null,
        comprador_telefono: buyer.comprador_telefono || null,
        forma_pago: buyer.forma_pago,
        notas: buyer.notas || null,
      })
      setDone(v)
      setStep(3)
    } catch (e) {
      setError(e.message || 'Error al registrar venta.')
    } finally {
      setSaving(false)
    }
  }

  if (step === 3 && done) return (
    <div>
      <TopBar onLogout={onLogout} />
      <div className="main" style={{ maxWidth: 540, margin: '60px auto', textAlign: 'center' }}>
        <div style={{ width: 64, height: 64, borderRadius: '50%', background: 'var(--c-success-tint)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px' }}>
          <Icon name="check" size={28} style={{ stroke: 'var(--c-success)' }} />
        </div>
        <h2 style={{ margin: '0 0 8px' }}>Venta registrada</h2>
        <p style={{ color: 'var(--c-fg-2)', margin: '0 0 24px' }}>
          {selected.marca} {selected.modelo} {selected.anio} vendido a <strong>{buyer.comprador_nombre}</strong>
        </p>
        <div style={{ display: 'flex', gap: 10, justifyContent: 'center' }}>
          <button className="btn secondary" onClick={() => {
            setStep(1); setSelected(null)
            setBuyer({ comprador_nombre: '', comprador_dni: '', comprador_telefono: '', precio_final: '', moneda_precio: 'USD', forma_pago: 'Efectivo', vendedor_id: '', notas: '' })
            setDone(null)
            getVehiculos({ estado: 'disponible' }).then(setVehiculos)
          }}>
            Registrar otra venta
          </button>
          <a className="btn primary" href={`/vehiculo/${selected.id}`}>
            Ver vehículo
          </a>
        </div>
      </div>
    </div>
  )

  return (
    <div>
      <TopBar onLogout={onLogout} />
      <div className="main">
        <div className="page-head">
          <div>
            <h1 className="page-title">Registrar venta</h1>
            <p className="page-caption">Paso {step} de 2</p>
          </div>
          <div style={{ flex: 1 }} />
          <div className="seg">
            <button className={step === 1 ? 'on' : ''} onClick={() => step > 1 && setStep(1)}>
              <Icon name="car" size={13} /> Vehículo
            </button>
            <button className={step === 2 ? 'on' : ''} disabled={!selected}>
              <Icon name="users" size={13} /> Comprador
            </button>
          </div>
        </div>

        {error && <div className="banner warning"><Icon name="alert" size={16} />{error}</div>}

        {step === 1 && (
          <div>
            <p style={{ color: 'var(--c-fg-2)', marginBottom: 12 }}>Seleccioná el vehículo a vender:</p>
            {vehiculos.length === 0
              ? <div className="banner info"><Icon name="info" size={16} />No hay vehículos disponibles.</div>
              : vehiculos.map(v => (
                <div key={v.id}
                  className="list-row"
                  onClick={() => { setSelected(v); setBuyer(p => ({ ...p, precio_final: v.precio_base || '' })); setStep(2) }}
                  style={{ cursor: 'pointer' }}>
                  <div>
                    <div className="v-title">{v.marca} {v.modelo} {v.anio}{v.version ? ` · ${v.version}` : ''}</div>
                    <div className="v-meta">{v.patente || '—'} · #{v.id}</div>
                  </div>
                  <StateBadge estado={v.estado} />
                  <div className="num">{v.km_hs?.toLocaleString('es-AR') || '0'} km</div>
                  <div className="price-cell">
                    <strong>USD {v.precio_base?.toLocaleString('es-AR')}</strong>
                  </div>
                  <Icon name="chev-r" size={16} style={{ stroke: 'var(--c-fg-2)', justifySelf: 'end' }} />
                </div>
              ))
            }
          </div>
        )}

        {step === 2 && selected && (
          <div>
            <div className="banner info" style={{ marginBottom: 16 }}>
              <Icon name="car" size={16} />
              <span><strong>{selected.marca} {selected.modelo} {selected.anio}</strong> — USD {selected.precio_base?.toLocaleString('es-AR')}</span>
              <button className="btn ghost" style={{ marginLeft: 'auto', padding: '2px 8px' }} onClick={() => setStep(1)}>Cambiar</button>
            </div>
            <div className="card">
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
                <FormField label="Nombre comprador" required>
                  <input className="input" placeholder="Juan Pérez" value={buyer.comprador_nombre} onChange={f('comprador_nombre')} />
                </FormField>
                <FormField label="DNI">
                  <input className="input" placeholder="12345678" value={buyer.comprador_dni} onChange={f('comprador_dni')} />
                </FormField>
                <FormField label="Teléfono">
                  <input className="input" placeholder="+54 9 11 1234 5678" value={buyer.comprador_telefono} onChange={f('comprador_telefono')} />
                </FormField>
                <FormField label="Forma de pago">
                  <select className="input" value={buyer.forma_pago} onChange={f('forma_pago')}>
                    {FORMAS.map(fm => <option key={fm} value={fm}>{fm}</option>)}
                  </select>
                </FormField>
                <FormField label="Precio final" required>
                  <input className="input" type="number" value={buyer.precio_final} onChange={f('precio_final')} />
                </FormField>
                <FormField label="Moneda">
                  <select className="input" value={buyer.moneda_precio} onChange={f('moneda_precio')}>
                    <option value="USD">USD</option>
                    <option value="ARS">ARS</option>
                  </select>
                </FormField>
                <FormField label="Vendedor">
                  <select className="input" value={buyer.vendedor_id} onChange={f('vendedor_id')}>
                    <option value="">Sin asignar</option>
                    {vendedores.map(vn => <option key={vn.id} value={vn.id}>{vn.nombre}</option>)}
                  </select>
                </FormField>
                <FormField label="Notas">
                  <textarea className="input" rows={2} value={buyer.notas} onChange={f('notas')} style={{ resize: 'vertical' }} />
                </FormField>
              </div>
            </div>
            <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', marginTop: 16 }}>
              <button className="btn secondary" onClick={() => setStep(1)}><Icon name="arrow-l" size={14} /> Atrás</button>
              <button className="btn primary" onClick={confirm} disabled={saving}>
                {saving ? 'Registrando…' : <><Icon name="check" size={14} /> Confirmar venta</>}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
