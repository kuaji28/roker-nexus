import { useEffect, useState } from 'react'
import TopBar from '../components/TopBar'
import Icon from '../components/Icon'
import FormField from '../components/FormField'
import { updatePin, getTC, updateTC } from '../lib/supabase'

export default function Config({ onLogout }) {
  const [pin, setPin]           = useState({ new1: '', new2: '' })
  const [pinMsg, setPinMsg]     = useState(null)
  const [tc, setTc]             = useState('')
  const [tcMsg, setTcMsg]       = useState(null)
  const [savingPin, setSavingPin] = useState(false)
  const [savingTc, setSavingTc]   = useState(false)

  useEffect(() => { getTC().then(v => setTc(String(v))) }, [])

  async function changePin() {
    setPinMsg(null)
    if (!pin.new1 || pin.new1.length < 4) { setPinMsg({ type: 'warning', text: 'El PIN debe tener al menos 4 dígitos.' }); return }
    if (pin.new1 !== pin.new2) { setPinMsg({ type: 'warning', text: 'Los PINs no coinciden.' }); return }
    setSavingPin(true)
    try {
      await updatePin(pin.new1)
      setPinMsg({ type: 'success', text: 'PIN actualizado correctamente.' })
      setPin({ new1: '', new2: '' })
    } catch (e) {
      setPinMsg({ type: 'warning', text: e.message || 'Error al cambiar PIN.' })
    } finally {
      setSavingPin(false)
    }
  }

  async function changeTc() {
    const v = Number(tc)
    if (!v || v < 100) { setTcMsg({ type: 'warning', text: 'Ingresá un tipo de cambio válido.' }); return }
    setSavingTc(true)
    try {
      await updateTC(v)
      setTcMsg({ type: 'success', text: 'Tipo de cambio actualizado.' })
    } catch (e) {
      setTcMsg({ type: 'warning', text: e.message })
    } finally {
      setSavingTc(false)
    }
  }

  const fp = (k) => (e) => setPin(p => ({ ...p, [k]: e.target.value }))

  return (
    <div>
      <TopBar onLogout={onLogout} />
      <div className="main" style={{ maxWidth: 560 }}>
        <div className="page-head">
          <div>
            <h1 className="page-title">Configuración</h1>
            <p className="page-caption">Ajustes del sistema GH Cars</p>
          </div>
        </div>

        <div className="card" style={{ marginBottom: 16 }}>
          <h3 style={{ margin: '0 0 16px', fontSize: 15, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 6 }}>
            <Icon name="cog" size={14} /> Cambiar PIN de acceso
          </h3>
          <div style={{ display: 'grid', gap: 12 }}>
            <FormField label="PIN nuevo">
              <input className="input" type="password" placeholder="····" value={pin.new1} onChange={fp('new1')} maxLength={20} />
            </FormField>
            <FormField label="Confirmar PIN">
              <input className="input" type="password" placeholder="····" value={pin.new2} onChange={fp('new2')} maxLength={20} />
            </FormField>
            {pinMsg && (
              <div className={`banner ${pinMsg.type}`}>
                <Icon name={pinMsg.type === 'success' ? 'check' : 'alert'} size={16} />{pinMsg.text}
              </div>
            )}
            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <button className="btn primary" onClick={changePin} disabled={savingPin}>
                {savingPin ? 'Guardando…' : <><Icon name="check" size={14} /> Guardar PIN</>}
              </button>
            </div>
          </div>
        </div>

        <div className="card">
          <h3 style={{ margin: '0 0 16px', fontSize: 15, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 6 }}>
            <Icon name="cash" size={14} /> Tipo de cambio USD/ARS
          </h3>
          <div style={{ display: 'grid', gap: 12 }}>
            <FormField label="$ ARS por 1 USD" hint="Se usa para mostrar precios en pesos en toda la app">
              <input className="input" type="number" value={tc} onChange={e => setTc(e.target.value)} placeholder="1415" min={1} />
            </FormField>
            {tcMsg && (
              <div className={`banner ${tcMsg.type}`}>
                <Icon name={tcMsg.type === 'success' ? 'check' : 'alert'} size={16} />{tcMsg.text}
              </div>
            )}
            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <button className="btn primary" onClick={changeTc} disabled={savingTc}>
                {savingTc ? 'Guardando…' : <><Icon name="check" size={14} /> Actualizar TC</>}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
