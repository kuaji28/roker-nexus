import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import TopBar from '../components/TopBar'
import Icon from '../components/Icon'
import FormField from '../components/FormField'
import { createVehiculo, uploadFoto } from '../lib/supabase'

const TIPOS  = ['auto', 'moto', 'cuatriciclo', 'moto_de_agua']
const ESTADOS = ['disponible', 'en_revision', 'en_preparacion']
const COMB   = ['Nafta', 'Diésel', 'GNC', 'Híbrido', 'Eléctrico']
const TRANS  = ['Manual', 'Automática', 'CVT', 'Semi-automática']

function Step1({ form, set }) {
  const f = (k) => (e) => set(p => ({ ...p, [k]: e.target.value }))
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
      <FormField label="Tipo" required>
        <select className="input" value={form.tipo} onChange={f('tipo')}>
          {TIPOS.map(t => <option key={t} value={t}>{t.replace('_', ' ')}</option>)}
        </select>
      </FormField>
      <FormField label="Estado">
        <select className="input" value={form.estado} onChange={f('estado')}>
          {ESTADOS.map(e => <option key={e} value={e}>{e.replace('_', ' ')}</option>)}
        </select>
      </FormField>
      <FormField label="Marca" required>
        <input className="input" placeholder="Toyota" value={form.marca} onChange={f('marca')} />
      </FormField>
      <FormField label="Modelo" required>
        <input className="input" placeholder="Corolla" value={form.modelo} onChange={f('modelo')} />
      </FormField>
      <FormField label="Año" required>
        <input className="input" type="number" placeholder="2022" value={form.anio} onChange={f('anio')} min={1960} max={2030} />
      </FormField>
      <FormField label="Versión">
        <input className="input" placeholder="XEI CVT" value={form.version} onChange={f('version')} />
      </FormField>
      <FormField label="Patente">
        <input className="input" placeholder="AB123CD" value={form.patente} onChange={f('patente')} style={{ textTransform: 'uppercase' }} />
      </FormField>
      <FormField label="Color">
        <input className="input" placeholder="Blanco perla" value={form.color} onChange={f('color')} />
      </FormField>
      <FormField label="Km / Hs">
        <input className="input" type="number" placeholder="45000" value={form.km_hs} onChange={f('km_hs')} min={0} />
      </FormField>
      <FormField label="Precio base (USD)" required>
        <input className="input" type="number" placeholder="18000" value={form.precio_base} onChange={f('precio_base')} min={0} />
      </FormField>
      <FormField label="Costo compra (USD)">
        <input className="input" type="number" placeholder="15000" value={form.costo_compra} onChange={f('costo_compra')} min={0} />
      </FormField>
      <FormField label="Combustible">
        <select className="input" value={form.combustible} onChange={f('combustible')}>
          <option value="">—</option>
          {COMB.map(c => <option key={c} value={c}>{c}</option>)}
        </select>
      </FormField>
      <FormField label="Transmisión">
        <select className="input" value={form.transmision} onChange={f('transmision')}>
          <option value="">—</option>
          {TRANS.map(t => <option key={t} value={t}>{t}</option>)}
        </select>
      </FormField>
      <FormField label="Origen">
        <select className="input" value={form.origen} onChange={f('origen')}>
          <option value="compra_directa">Compra directa</option>
          <option value="parte_de_pago">Parte de pago</option>
          <option value="consignacion">Consignación</option>
        </select>
      </FormField>
      <FormField label="Nro Motor">
        <input className="input" placeholder="ABC123" value={form.nro_motor} onChange={f('nro_motor')} />
      </FormField>
      <FormField label="Nro Chasis">
        <input className="input" placeholder="XYZ456" value={form.nro_chasis} onChange={f('nro_chasis')} />
      </FormField>
      <div style={{ gridColumn: '1 / -1' }}>
        <FormField label="Notas internas">
          <textarea className="input" rows={3} placeholder="Observaciones, detalles del vehículo..."
            value={form.notas_internas} onChange={f('notas_internas')}
            style={{ resize: 'vertical' }} />
        </FormField>
      </div>
    </div>
  )
}

function Step2({ files, setFiles, previews, setPreviews }) {
  function handleFiles(newFiles) {
    const imgs = Array.from(newFiles).filter(f => f.type.startsWith('image/'))
    setFiles(p => [...p, ...imgs])
    imgs.forEach(f => {
      const r = new FileReader()
      r.onload = ev => setPreviews(p => [...p, ev.target.result])
      r.readAsDataURL(f)
    })
  }
  function remove(i) {
    setFiles(p => p.filter((_, j) => j !== i))
    setPreviews(p => p.filter((_, j) => j !== i))
  }
  return (
    <div>
      <div
        onDrop={e => { e.preventDefault(); handleFiles(e.dataTransfer.files) }}
        onDragOver={e => e.preventDefault()}
        onClick={() => document.getElementById('foto-input').click()}
        style={{
          border: '2px dashed var(--c-border)', borderRadius: 'var(--r-lg)',
          padding: 40, textAlign: 'center', cursor: 'pointer', color: 'var(--c-fg-2)',
          marginBottom: 16,
        }}
      >
        <Icon name="image" size={32} style={{ stroke: 'var(--c-fg-3)', display: 'block', margin: '0 auto 8px' }} />
        <div style={{ fontWeight: 600, marginBottom: 4 }}>Arrastrá fotos o hacé click</div>
        <div style={{ fontSize: 12, color: 'var(--c-fg-3)' }}>JPG, PNG, WEBP — múltiples archivos</div>
        <input id="foto-input" type="file" accept="image/*" multiple style={{ display: 'none' }}
          onChange={e => handleFiles(e.target.files)} />
      </div>
      {previews.length > 0 && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(120px, 1fr))', gap: 8 }}>
          {previews.map((src, i) => (
            <div key={i} style={{ position: 'relative', aspectRatio: '4/3', borderRadius: 'var(--r)', overflow: 'hidden' }}>
              <img src={src} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
              <button onClick={() => remove(i)} style={{
                position: 'absolute', top: 4, right: 4,
                background: 'rgba(0,0,0,.6)', border: 'none', borderRadius: '50%',
                width: 24, height: 24, cursor: 'pointer', color: '#fff',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                <Icon name="x" size={12} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default function Ingreso({ onLogout }) {
  const navigate = useNavigate()
  const [step, setStep]     = useState(1)
  const [saving, setSaving] = useState(false)
  const [error, setError]   = useState('')
  const [files, setFiles]   = useState([])
  const [previews, setPreviews] = useState([])
  const [form, setForm] = useState({
    tipo: 'auto', marca: '', modelo: '', anio: '', version: '',
    patente: '', color: '', km_hs: '', precio_base: '', costo_compra: '',
    combustible: '', transmision: '', origen: 'compra_directa',
    nro_motor: '', nro_chasis: '', notas_internas: '', estado: 'disponible',
  })

  async function handleSubmit() {
    if (!form.marca || !form.modelo || !form.anio || !form.precio_base) {
      setError('Completá los campos obligatorios: Marca, Modelo, Año y Precio.')
      setStep(1)
      return
    }
    setSaving(true)
    setError('')
    try {
      const payload = {
        ...form,
        anio: Number(form.anio),
        km_hs: form.km_hs ? Number(form.km_hs) : null,
        precio_base: Number(form.precio_base),
        costo_compra: form.costo_compra ? Number(form.costo_compra) : null,
        patente: form.patente ? form.patente.toUpperCase() : null,
      }
      const v = await createVehiculo(payload)
      for (const file of files) {
        await uploadFoto(v.id, file)
      }
      navigate(`/vehiculo/${v.id}`)
    } catch (e) {
      setError(e.message || 'Error al guardar.')
      setSaving(false)
    }
  }

  return (
    <div>
      <TopBar onLogout={onLogout} />
      <div className="main">
        <div className="page-head">
          <div>
            <h1 className="page-title">Ingresar vehículo</h1>
            <p className="page-caption">Paso {step} de 2 — {step === 1 ? 'Datos del vehículo' : 'Fotos'}</p>
          </div>
          <div style={{ flex: 1 }} />
          <div className="seg">
            <button className={step === 1 ? 'on' : ''} onClick={() => setStep(1)}>
              <Icon name="clipboard" size={13} /> Datos
            </button>
            <button className={step === 2 ? 'on' : ''} onClick={() => setStep(2)}>
              <Icon name="image" size={13} /> Fotos
            </button>
          </div>
        </div>

        {error && (
          <div className="banner warning">
            <Icon name="alert" size={16} />{error}
          </div>
        )}

        <div className="card" style={{ marginBottom: 20 }}>
          {step === 1
            ? <Step1 form={form} set={setForm} />
            : <Step2 files={files} setFiles={setFiles} previews={previews} setPreviews={setPreviews} />
          }
        </div>

        <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
          {step === 2 && (
            <button className="btn secondary" onClick={() => setStep(1)}>
              <Icon name="arrow-l" size={14} /> Atrás
            </button>
          )}
          {step === 1 && (
            <button className="btn primary" onClick={() => setStep(2)}>
              Siguiente <Icon name="chev-r" size={14} />
            </button>
          )}
          {step === 2 && (
            <button className="btn primary" onClick={handleSubmit} disabled={saving}>
              {saving ? 'Guardando…' : <><Icon name="check" size={14} /> Guardar vehículo</>}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
