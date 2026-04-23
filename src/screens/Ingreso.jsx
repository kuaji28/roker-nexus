import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import TopBar from '../components/TopBar'
import Icon from '../components/Icon'
import FormField from '../components/FormField'
import { createVehiculo, uploadFoto } from '../lib/supabase'
import { callAI, callAIFiles, aiConfigured } from '../lib/api'

const TIPOS   = ['auto', 'moto', 'cuatriciclo', 'moto_de_agua']
const ESTADOS = ['disponible', 'en_revision', 'en_preparacion']
const COMB    = ['Nafta', 'Diésel', 'GNC', 'Híbrido', 'Eléctrico']
const TRANS   = ['Manual', 'Automática', 'CVT', 'Semi-automática']

const CARROCERIA_TIPO_MAP = {
  sedan: 'auto', sedán: 'auto', hatchback: 'auto', suv: 'auto', pickup: 'auto',
  'pick-up': 'auto', coupe: 'auto', coupé: 'auto', minivan: 'auto', van: 'auto',
  rural: 'auto', cabrio: 'auto', convertible: 'auto', auto: 'auto',
  automóvil: 'auto', automovil: 'auto', furgon: 'auto', furgón: 'auto',
  berlina: 'auto', roadster: 'auto',
  moto: 'moto', motocicleta: 'moto', scooter: 'moto', enduro: 'moto', trial: 'moto',
  cuatriciclo: 'cuatriciclo', atv: 'cuatriciclo', quad: 'cuatriciclo',
  'moto de agua': 'moto_de_agua', 'jet ski': 'moto_de_agua', jetski: 'moto_de_agua',
  motonaútica: 'moto_de_agua', motonauta: 'moto_de_agua',
}

function carroceriaToTipo(carroceria) {
  if (!carroceria) return null
  return CARROCERIA_TIPO_MAP[carroceria.toLowerCase().trim()] || null
}

// ISO 3779 position 10 VIN year decode — same logic as Streamlit vin_decoder.py
const VIN_ANIO_MAP = {
  A:2010, B:2011, C:2012, D:2013, E:2014, F:2015, G:2016, H:2017,
  J:2018, K:2019, L:2020, M:2021, N:2022, P:2023, R:2024, S:2025,
  T:2026, V:2027, W:2028, X:2029, Y:2030,
  '1':2001,'2':2002,'3':2003,'4':2004,'5':2005,
  '6':2006,'7':2007,'8':2008,'9':2009,
}
function anioDesdeVin(vin) {
  if (!vin || vin.length < 10) return null
  return VIN_ANIO_MAP[vin[9].toUpperCase()] || null
}

function validatePatente(pat) {
  const p = (pat || '').toUpperCase().replace(/[\s\-]/g, '')
  if (!p) return true
  // Mercosur AB123CD, old ABC123, moto A123BCD and similar 6-8 char alphanumeric
  return /^[A-Z]{2}\d{3}[A-Z]{2}$/.test(p)
      || /^[A-Z]{3}\d{3}$/.test(p)
      || /^[A-Z0-9]{5,8}$/.test(p)
}

function parseFechaDMY(str) {
  if (!str) return null
  const m = str.match(/^(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})$/)
  if (m) return new Date(+m[3], +m[2] - 1, +m[1])
  const iso = str.match(/^(\d{4})[\/\-](\d{2})[\/\-](\d{2})$/)
  if (iso) return new Date(+iso[1], +iso[2] - 1, +iso[3])
  return null
}

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
  const [step, setStep]         = useState(1)
  const [saving, setSaving]     = useState(false)
  const [error, setError]       = useState('')
  const [aiLoading, setAiLoading] = useState('')
  const [aiMsg, setAiMsg]       = useState(null)
  const [aiWarnings, setAiWarnings] = useState([])
  const [isDragging, setIsDragging] = useState(false)
  const [files, setFiles]       = useState([])
  const [previews, setPreviews] = useState([])
  const [form, setForm] = useState({
    tipo: 'auto', marca: '', modelo: '', anio: '', version: '',
    patente: '', color: '', km_hs: '', precio_base: '', costo_compra: '',
    combustible: '', transmision: '', origen: 'compra_directa',
    nro_motor: '', nro_chasis: '', notas_internas: '', estado: 'disponible',
  })

  async function _completarSpecs(marca, modelo, anio, version, nro_motor, nro_chasis) {
    if (!marca || !modelo || !anio) return null
    const specs = await callAI('/ai/completar-specs', {
      marca, modelo, anio: Number(anio), version, nro_motor, nro_chasis,
    })
    setForm(p => ({
      ...p,
      combustible: specs.combustible || p.combustible,
      transmision: specs.transmision || p.transmision,
    }))
    return specs
  }

  async function handleCedulaFiles(e) {
    const fls = Array.from(e.target.files)
    if (!fls.length) return
    setAiLoading('cedula'); setAiMsg(null); setAiWarnings([])
    try {
      const data = await callAIFiles('/ai/ocr-cedula', fls)
      const warnings = []

      // Map carrocería → tipo de vehículo
      const tipoDetectado = carroceriaToTipo(data.carroceria)

      // Validate año — fallback to VIN decode if OCR didn't get it
      let anioFinal = null
      let anioFuente = ''
      const anioNum = data.anio ? Number(data.anio) : null
      if (anioNum && anioNum >= 1960 && anioNum <= 2030) {
        anioFinal = String(anioNum)
        anioFuente = 'OCR'
      } else {
        if (data.anio) warnings.push(`Año detectado fuera de rango (${data.anio}) — se intentó VIN`)
        const anioVin = anioDesdeVin(data.nro_chasis || '')
        if (anioVin) {
          anioFinal = String(anioVin)
          anioFuente = 'VIN'
        }
      }

      // Validate patente
      const patenteVal = data.patente || ''
      if (patenteVal && !validatePatente(patenteVal)) {
        warnings.push(`Patente con formato inusual (${patenteVal}) — verificar`)
      }

      // Check vencimiento cédula
      if (data.vencimiento_cedula) {
        const venc = parseFechaDMY(data.vencimiento_cedula)
        if (venc && venc < new Date()) {
          warnings.push(`⚠️ Cédula VENCIDA el ${data.vencimiento_cedula} — verificar documentación`)
        }
      }

      // campos_dudosos
      if (data.campos_dudosos?.length) {
        warnings.push(`Campos a verificar: ${data.campos_dudosos.join(', ')}`)
      }

      // Build notas extras from titular, DNI, fechas
      const notasExtras = []
      if (data.titular) notasExtras.push(`Titular: ${data.titular}`)
      if (data.dni_titular) notasExtras.push(`DNI: ${data.dni_titular}`)
      if (data.fecha_inscripcion) notasExtras.push(`Inscripción: ${data.fecha_inscripcion}`)
      if (data.vencimiento_cedula) notasExtras.push(`Venc. cédula: ${data.vencimiento_cedula}`)

      if (anioFuente === 'VIN') warnings.push(`Año derivado del VIN (${anioFinal}) — confirmar`)

      setForm(p => {
        const notasAdd = notasExtras.length
          ? (p.notas_internas ? p.notas_internas + '\n' : '') + notasExtras.join(' | ')
          : p.notas_internas
        return {
          ...p,
          tipo: tipoDetectado || p.tipo,
          marca: data.marca || p.marca,
          modelo: data.modelo || p.modelo,
          anio: anioFinal || p.anio,
          version: data.version || p.version,
          patente: patenteVal || p.patente,
          color: data.color || p.color,
          nro_motor: data.nro_motor || p.nro_motor,
          nro_chasis: data.nro_chasis || p.nro_chasis,
          notas_internas: notasAdd,
        }
      })

      setAiWarnings(warnings)

      const confBaja = data.confianza_general === 'baja'
      const marcaOcr = data.marca || ''
      const modeloOcr = data.modelo || ''
      const anioOcr = anioFinal || ''

      if (confBaja) {
        setAiMsg({ type: 'warning', text: 'Cédula leída con confianza baja — revisar todos los campos antes de continuar.' })
      } else {
        let specsMsg = ''
        let specsWarning = ''
        if (marcaOcr && modeloOcr) {
          setAiLoading('specs')
          try {
            const specs = await _completarSpecs(marcaOcr, modeloOcr, anioOcr, data.version || '', data.nro_motor || '', data.nro_chasis || '')
            if (specs) specsMsg = ` · ${specs.combustible || '—'} / ${specs.transmision || '—'}`
          } catch (e) {
            specsWarning = `Specs no completadas: ${e.message}`
          }
        }
        if (specsWarning) warnings.push(specsWarning)
        const anioNote = anioFuente === 'VIN' ? ` Año del VIN (${anioFinal}).` : ''
        setAiMsg({
          type: 'success',
          text: `Cédula leída. Datos autocargados.${tipoDetectado ? ` Tipo: ${tipoDetectado}.` : ''}${anioNote}${specsMsg}`,
        })
      }
    } catch (err) {
      setAiMsg({ type: 'warning', text: 'Error IA: ' + err.message })
    } finally { setAiLoading(''); e.target.value = '' }
  }

  async function handleCompletarSpecs() {
    if (!form.marca || !form.modelo) return
    setAiLoading('specs'); setAiMsg(null)
    try {
      const specs = await _completarSpecs(
        form.marca, form.modelo, form.anio, form.version, form.nro_motor, form.nro_chasis
      )
      if (specs) {
        setAiMsg({ type: 'success', text: `Specs completadas. Combustible: ${specs.combustible || '—'} · Trans: ${specs.transmision || '—'} · ${specs.potencia_hp || '?'} HP` })
      }
    } catch (err) {
      setAiMsg({ type: 'warning', text: 'Error IA: ' + err.message })
    } finally { setAiLoading('') }
  }

  async function handleSugerirPrecio() {
    if (!form.marca || !form.modelo) return
    setAiLoading('precio'); setAiMsg(null)
    try {
      const data = await callAI('/ai/sugerir-precio', {
        marca: form.marca, modelo: form.modelo, anio: Number(form.anio),
        version: form.version, km: Number(form.km_hs) || 0,
      })
      setForm(p => ({ ...p, precio_base: String(data.precio_sugerido || p.precio_base) }))
      setAiMsg({ type: 'info', text: `Precio sugerido: USD ${data.precio_sugerido?.toLocaleString('es-AR')} (rango: ${data.precio_min?.toLocaleString('es-AR')} – ${data.precio_max?.toLocaleString('es-AR')}) — confianza: ${data.confianza}` })
    } catch (err) {
      setAiMsg({ type: 'warning', text: 'Error IA: ' + err.message })
    } finally { setAiLoading('') }
  }

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

        {step === 1 && aiConfigured() && (
          <div
            className="card"
            style={{ marginBottom: 12, outline: isDragging ? '2px dashed var(--c-accent)' : 'none' }}
            onDragOver={e => { e.preventDefault(); setIsDragging(true) }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={e => {
              e.preventDefault(); setIsDragging(false)
              const imgs = Array.from(e.dataTransfer.files).filter(f => f.type.startsWith('image/'))
              if (imgs.length) handleCedulaFiles({ target: { files: imgs, value: '' } })
            }}
          >
            <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
              <span style={{ fontSize: 12, color: 'var(--c-fg-2)', fontWeight: 600 }}>
                Asistente IA {isDragging && <span style={{ color: 'var(--c-accent)' }}>— soltá la foto aquí</span>}
              </span>
              <button className="btn secondary" disabled={!!aiLoading}
                onClick={() => document.getElementById('cedula-scan').click()}>
                <Icon name="image" size={14} />
                {aiLoading === 'cedula' ? 'Escaneando…' : aiLoading === 'specs' ? 'Completando specs…' : 'Escanear cédula verde'}
              </button>
              <button className="btn secondary" disabled={!!aiLoading || !form.marca || !form.modelo}
                onClick={handleCompletarSpecs}>
                <Icon name="cog" size={14} />
                {aiLoading === 'specs' ? 'Completando…' : 'Completar specs'}
              </button>
              <button className="btn secondary" disabled={!!aiLoading || !form.marca || !form.modelo}
                onClick={handleSugerirPrecio}>
                <Icon name="tag" size={14} />
                {aiLoading === 'precio' ? 'Analizando…' : 'Sugerir precio'}
              </button>
              <input id="cedula-scan" type="file" accept="image/*" multiple style={{ display: 'none' }}
                onChange={handleCedulaFiles} />
            </div>
            {aiMsg && (
              <div className={`banner ${aiMsg.type}`} style={{ marginTop: 10, marginBottom: aiWarnings.length ? 6 : 0 }}>
                <Icon name={aiMsg.type === 'success' ? 'check' : aiMsg.type === 'warning' ? 'alert' : 'info'} size={16} />
                {aiMsg.text}
              </div>
            )}
            {aiWarnings.length > 0 && (
              <div style={{ marginTop: 6, display: 'flex', flexDirection: 'column', gap: 4 }}>
                {aiWarnings.map((w, i) => (
                  <div key={i} className="banner warning" style={{ marginBottom: 0, fontSize: 12 }}>
                    <Icon name="alert" size={14} />{w}
                  </div>
                ))}
              </div>
            )}
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
