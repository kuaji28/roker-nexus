import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import TopBar from '../components/TopBar'
import Icon from '../components/Icon'
import FormField from '../components/FormField'
import { createVehiculo, uploadFoto, uploadFotoVehiculo, saveFotoRecord, getVendedores } from '../lib/supabase'
import { callAI, callAIFiles, aiConfigured } from '../lib/api'

const TIPOS      = ['auto', 'moto', 'cuatriciclo', 'moto_de_agua']
const ESTADOS    = ['disponible', 'en_revision', 'en_preparacion']
const COMB       = ['Nafta', 'Diésel', 'GNC', 'Híbrido', 'Eléctrico']
const TRANS      = ['Manual', 'Automática', 'CVT', 'Semi-automática']
const UBICACIONES = [
  { value: 'showroom', label: 'Showroom'    },
  { value: 'taller',   label: 'Taller'      },
  { value: 'cochera',  label: 'Cochera'     },
  { value: 'traslado', label: 'En traslado' },
  { value: 'cliente',  label: 'En cliente'  },
]
const RECON_ESTADOS = [
  { value: 'ingresado',        label: 'Ingresado'        },
  { value: 'inspeccion',       label: 'En inspección'    },
  { value: 'mecanica',         label: 'En mecánica'      },
  { value: 'detailing',        label: 'En detailing'     },
  { value: 'fotos_pendientes', label: 'Fotos pendientes' },
  { value: 'listo',            label: 'Listo para venta' },
  { value: 'publicado',        label: 'Publicado'        },
]

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

function Step1({ form, set, vendedores }) {
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
      <FormField label="Ubicación">
        <select className="input" value={form.ubicacion} onChange={f('ubicacion')}>
          {UBICACIONES.map(u => <option key={u.value} value={u.value}>{u.label}</option>)}
        </select>
      </FormField>
      <FormField label="Estado reacond.">
        <select className="input" value={form.estado_recon} onChange={f('estado_recon')}>
          {RECON_ESTADOS.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
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
      <FormField label="Precio lista (USD)" hint="Precio visible para clientes">
        <input className="input" type="number" placeholder={form.precio_base || "20000"}
          value={form.precio_lista || ''} onChange={f('precio_lista')} min={0} />
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
      <FormField label="Responsable (quien ingresa)">
        <select className="input" value={form.responsable_id} onChange={f('responsable_id')}>
          <option value="">Sin asignar</option>
          {vendedores.map(v => <option key={v.id} value={v.id}>{v.nombre}</option>)}
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

const SECCIONES_SPECS = [
  {
    titulo: '⚙️ Técnico',
    campos: [
      { key: 'potencia_hp', label: 'Potencia (HP)', tipo: 'number', placeholder: '150' },
      { key: 'torque_nm', label: 'Torque (Nm)', tipo: 'number', placeholder: '200' },
      { key: 'cilindros', label: 'Cilindros', tipo: 'number', placeholder: '4' },
      { key: 'vel_max_kmh', label: 'Vel. máx (km/h)', tipo: 'number', placeholder: '200' },
      { key: 'aceleracion_0_100', label: '0-100 km/h (s)', tipo: 'number', placeholder: '9.5', step: 0.1 },
      { key: 'tanque_litros', label: 'Tanque (litros)', tipo: 'number', placeholder: '50' },
      { key: 'consumo_mixto', label: 'Consumo mixto (L/100km)', tipo: 'number', placeholder: '7.5', step: 0.1 },
      { key: 'peso_kg', label: 'Peso (kg)', tipo: 'number', placeholder: '1300' },
    ],
  },
  {
    titulo: '❄️ Climatización',
    campos: [
      {
        key: 'climatizacion', label: 'Climatización', tipo: 'select',
        opciones: [
          { v: '', l: '— Sin datos —' },
          { v: 'sin_ac', l: 'Sin aire acondicionado' },
          { v: 'manual', l: 'Aire manual' },
          { v: 'automatico', l: 'Aire automático' },
          { v: 'bizona', l: 'Bizona' },
        ],
      },
    ],
  },
  {
    titulo: '📺 Multimedia',
    campos: [
      { key: 'pantalla_pulg', label: 'Pantalla (pulgadas)', tipo: 'number', placeholder: '10.1', step: 0.1 },
      { key: 'apple_carplay', label: 'Apple CarPlay', tipo: 'bool' },
      { key: 'android_auto', label: 'Android Auto', tipo: 'bool' },
      { key: 'carga_inalambrica', label: 'Carga inalámbrica', tipo: 'bool' },
      { key: 'bluetooth', label: 'Bluetooth', tipo: 'bool' },
      { key: 'gps_integrado', label: 'GPS integrado', tipo: 'bool' },
    ],
  },
  {
    titulo: '🛋️ Confort',
    campos: [
      {
        key: 'faros', label: 'Faros', tipo: 'select',
        opciones: [
          { v: '', l: '— Sin datos —' },
          { v: 'halógenos', l: 'Halógenos' },
          { v: 'full_led', l: 'Full LED' },
          { v: 'bi_xenon', l: 'Bi-xenón' },
          { v: 'laser', l: 'Láser' },
        ],
      },
      {
        key: 'tapizado', label: 'Tapizado', tipo: 'select',
        opciones: [
          { v: '', l: '— Sin datos —' },
          { v: 'tela', l: 'Tela' },
          { v: 'semicuero', l: 'Semicuero' },
          { v: 'cuero', l: 'Cuero' },
          { v: 'alcantara', l: 'Alcántara' },
        ],
      },
      { key: 'asientos_calefaccionados', label: 'Asientos calefaccionados', tipo: 'bool' },
      { key: 'asientos_electricos', label: 'Asientos eléctricos', tipo: 'bool' },
      { key: 'vidrios_electricos', label: 'Vidrios eléctricos', tipo: 'bool' },
      { key: 'cierre_centralizado', label: 'Cierre centralizado', tipo: 'bool' },
      { key: 'techo_solar', label: 'Techo solar', tipo: 'bool' },
      { key: 'techo_panoramico', label: 'Techo panorámico', tipo: 'bool' },
      { key: 'llantas_aleacion', label: 'Llantas de aleación', tipo: 'bool' },
      { key: 'alarma', label: 'Alarma', tipo: 'bool' },
      { key: 'arranque_sin_llave', label: 'Arranque sin llave (keyless)', tipo: 'bool' },
      { key: 'freno_mano_electrico', label: 'Freno de mano eléctrico', tipo: 'bool' },
    ],
  },
  {
    titulo: '🛡️ Seguridad',
    campos: [
      { key: 'airbags', label: 'Airbags', tipo: 'number', placeholder: '6' },
      { key: 'camara_retroceso', label: 'Cámara de retroceso', tipo: 'bool' },
      { key: 'sensores_estacionamiento', label: 'Sensores de estacionamiento', tipo: 'bool' },
      { key: 'abs', label: 'ABS', tipo: 'bool' },
      { key: 'esp', label: 'ESP / Control de estabilidad', tipo: 'bool' },
      { key: 'control_crucero', label: 'Control crucero', tipo: 'bool' },
      { key: 'crucero_adaptativo', label: 'Crucero adaptativo (ACC)', tipo: 'bool' },
      { key: 'hud', label: 'HUD (head-up display)', tipo: 'bool' },
      { key: 'frenado_autonomo', label: 'Frenado autónomo de emergencia', tipo: 'bool' },
    ],
  },
]

function Step3({ form, setForm }) {
  const specs = form.specs || {}

  function setSpec(key, value) {
    setForm(p => ({ ...p, specs: { ...p.specs, [key]: value } }))
  }

  if (form.tipo !== 'auto') {
    return (
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
        <FormField label="Cilindrada (cc)">
          <input className="input" type="number" placeholder="1600"
            value={specs.cilindrada || ''} onChange={e => setSpec('cilindrada', e.target.value === '' ? null : Number(e.target.value))} />
        </FormField>
        <FormField label="Potencia (HP)">
          <input className="input" type="number" placeholder="150"
            value={specs.potencia_hp || ''} onChange={e => setSpec('potencia_hp', e.target.value === '' ? null : Number(e.target.value))} />
        </FormField>
        <FormField label="Torque (Nm)">
          <input className="input" type="number" placeholder="200"
            value={specs.torque_nm || ''} onChange={e => setSpec('torque_nm', e.target.value === '' ? null : Number(e.target.value))} />
        </FormField>
        <FormField label="Cilindros">
          <input className="input" type="number" placeholder="4"
            value={specs.cilindros || ''} onChange={e => setSpec('cilindros', e.target.value === '' ? null : Number(e.target.value))} />
        </FormField>
      </div>
    )
  }

  return (
    <div>
      {SECCIONES_SPECS.map(seccion => (
        <div key={seccion.titulo} style={{ marginBottom: 24 }}>
          <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 12,
                        borderBottom: '1px solid var(--c-border)', paddingBottom: 8 }}>
            {seccion.titulo}
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            {seccion.campos.map(campo => {
              if (campo.tipo === 'bool') {
                return (
                  <FormField key={campo.key} label={campo.label}>
                    <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
                      {[
                        { v: true, l: 'Sí' },
                        { v: false, l: 'No' },
                        { v: null, l: 'N/D' },
                      ].map(op => (
                        <label key={String(op.v)} style={{
                          display: 'flex', alignItems: 'center', gap: 4,
                          cursor: 'pointer', fontSize: 13,
                        }}>
                          <input type="radio"
                            checked={specs[campo.key] === op.v}
                            onChange={() => setSpec(campo.key, op.v)}
                          />
                          {op.l}
                        </label>
                      ))}
                    </div>
                  </FormField>
                )
              }
              if (campo.tipo === 'select') {
                return (
                  <FormField key={campo.key} label={campo.label}>
                    <select className="input"
                      value={specs[campo.key] || ''}
                      onChange={e => setSpec(campo.key, e.target.value || null)}>
                      {campo.opciones.map(op => (
                        <option key={op.v} value={op.v}>{op.l}</option>
                      ))}
                    </select>
                  </FormField>
                )
              }
              return (
                <FormField key={campo.key} label={campo.label}>
                  <input className="input" type={campo.tipo}
                    placeholder={campo.placeholder || ''}
                    step={campo.step || undefined}
                    value={specs[campo.key] ?? ''}
                    onChange={e => setSpec(campo.key, e.target.value === '' ? null : (campo.tipo === 'number' ? Number(e.target.value) : e.target.value))}
                  />
                </FormField>
              )
            })}
          </div>
        </div>
      ))}
    </div>
  )
}

const SHOT_LIST = [
  { key: 'frente_3_4_izq',  label: 'Frente 3/4 Izq.',  required: true,  icon: '📸' },
  { key: 'frente_3_4_der',  label: 'Frente 3/4 Der.',  required: true,  icon: '📸' },
  { key: 'lateral_izq',     label: 'Lateral Izq.',      required: true,  icon: '📸' },
  { key: 'lateral_der',     label: 'Lateral Der.',      required: true,  icon: '📸' },
  { key: 'trasero_3_4',     label: 'Trasero 3/4',       required: true,  icon: '📸' },
  { key: 'tablero',         label: 'Tablero',           required: true,  icon: '📸' },
  { key: 'asientos_del',    label: 'Asientos Del.',     required: false, icon: '📷' },
  { key: 'asientos_tras',   label: 'Asientos Tras.',    required: false, icon: '📷' },
  { key: 'baul',            label: 'Baúl/Maletero',     required: false, icon: '📷' },
  { key: 'odometro',        label: 'Odómetro',          required: false, icon: '📷' },
  { key: 'llantas',         label: 'Llantas',           required: false, icon: '📷' },
  { key: 'motor',           label: 'Motor',             required: false, icon: '📷' },
]

function Step2({ shotFiles, setShotFiles, shotPreviews, setShotPreviews, extraFiles, setExtraFiles, extraPreviews, setExtraPreviews }) {
  const requiredCount = SHOT_LIST.filter(s => s.required).length
  const uploadedRequired = SHOT_LIST.filter(s => s.required && shotFiles[s.key]).length
  const pct = requiredCount > 0 ? (uploadedRequired / requiredCount) * 100 : 0

  function handleShotFile(key, file) {
    if (!file || !file.type.startsWith('image/')) return
    setShotFiles(p => ({ ...p, [key]: file }))
    const r = new FileReader()
    r.onload = ev => setShotPreviews(p => ({ ...p, [key]: ev.target.result }))
    r.readAsDataURL(file)
  }

  function removeShot(key) {
    setShotFiles(p => { const n = { ...p }; delete n[key]; return n })
    setShotPreviews(p => { const n = { ...p }; delete n[key]; return n })
  }

  function handleExtraFiles(newFiles) {
    const imgs = Array.from(newFiles).filter(f => f.type.startsWith('image/'))
    setExtraFiles(p => [...p, ...imgs])
    imgs.forEach(f => {
      const r = new FileReader()
      r.onload = ev => setExtraPreviews(p => [...p, ev.target.result])
      r.readAsDataURL(f)
    })
  }

  function removeExtra(i) {
    setExtraFiles(p => p.filter((_, j) => j !== i))
    setExtraPreviews(p => p.filter((_, j) => j !== i))
  }

  return (
    <div>
      {/* Barra de progreso */}
      <div style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
          <span style={{ fontSize: 13, fontWeight: 600 }}>
            {uploadedRequired} de {requiredCount} fotos requeridas
          </span>
          <span style={{ fontSize: 12, color: 'var(--c-fg-3)' }}>
            {Object.keys(shotFiles).length} total cargadas
          </span>
        </div>
        <div style={{ height: 6, background: 'var(--c-border)', borderRadius: 3, overflow: 'hidden' }}>
          <div style={{
            height: '100%',
            width: `${pct}%`,
            background: pct === 100 ? '#22c55e' : 'var(--c-accent)',
            borderRadius: 3,
            transition: 'width .3s',
          }} />
        </div>
      </div>

      {/* Grilla 4 columnas */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10, marginBottom: 24 }}>
        {SHOT_LIST.map(shot => {
          const hasPhoto = !!shotFiles[shot.key]
          const preview = shotPreviews[shot.key]
          return (
            <div key={shot.key} style={{
              borderRadius: 'var(--r)',
              border: hasPhoto ? '2px solid var(--c-accent)' : '2px dashed var(--c-border)',
              overflow: 'hidden',
              background: 'var(--c-bg-2)',
            }}>
              <div style={{ aspectRatio: '4/3', position: 'relative' }}>
                {hasPhoto ? (
                  <>
                    <img src={preview} alt={shot.label}
                      style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }} />
                    <button
                      onClick={() => removeShot(shot.key)}
                      style={{
                        position: 'absolute', top: 4, right: 4,
                        background: 'rgba(0,0,0,.65)', border: 'none', borderRadius: '50%',
                        width: 22, height: 22, cursor: 'pointer', color: '#fff',
                        display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 0,
                      }}
                    >
                      <Icon name="x" size={11} />
                    </button>
                  </>
                ) : (
                  <label style={{
                    width: '100%', height: '100%', display: 'flex', flexDirection: 'column',
                    alignItems: 'center', justifyContent: 'center', cursor: 'pointer', gap: 4,
                  }}>
                    <span style={{ fontSize: 20 }}>{shot.icon}</span>
                    <span style={{ fontSize: 24, color: 'var(--c-fg-3)', lineHeight: 1 }}>+</span>
                    <input
                      type="file" accept="image/*" style={{ display: 'none' }}
                      onChange={e => { if (e.target.files[0]) handleShotFile(shot.key, e.target.files[0]); e.target.value = '' }}
                    />
                  </label>
                )}
              </div>
              <div style={{ padding: '5px 8px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 4 }}>
                <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--c-fg)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {shot.label}
                </span>
                <span style={{
                  fontSize: 9, fontWeight: 700, borderRadius: 3, padding: '1px 5px',
                  background: shot.required ? 'rgba(99,102,241,.12)' : 'var(--c-border)',
                  color: shot.required ? 'var(--c-accent)' : 'var(--c-fg-3)',
                  whiteSpace: 'nowrap', flexShrink: 0,
                }}>
                  {shot.required ? 'REQ' : 'OPC'}
                </span>
              </div>
            </div>
          )
        })}
      </div>

      {/* Fotos adicionales */}
      <div>
        <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 10, color: 'var(--c-fg-2)' }}>
          Fotos adicionales
        </div>
        <div
          onDrop={e => { e.preventDefault(); handleExtraFiles(e.dataTransfer.files) }}
          onDragOver={e => e.preventDefault()}
          onClick={() => document.getElementById('foto-extra-input').click()}
          style={{
            border: '2px dashed var(--c-border)', borderRadius: 'var(--r)',
            padding: '16px 24px', textAlign: 'center', cursor: 'pointer',
            color: 'var(--c-fg-3)', marginBottom: extraPreviews.length ? 10 : 0,
          }}
        >
          <Icon name="image" size={20} style={{ stroke: 'var(--c-fg-3)', display: 'block', margin: '0 auto 6px' }} />
          <div style={{ fontSize: 13 }}>Arrastrá o hacé click para agregar fotos extra</div>
          <input id="foto-extra-input" type="file" accept="image/*" multiple style={{ display: 'none' }}
            onChange={e => { handleExtraFiles(e.target.files); e.target.value = '' }} />
        </div>
        {extraPreviews.length > 0 && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(100px, 1fr))', gap: 8 }}>
            {extraPreviews.map((src, i) => (
              <div key={i} style={{ position: 'relative', aspectRatio: '4/3', borderRadius: 'var(--r)', overflow: 'hidden' }}>
                <img src={src} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                <button onClick={() => removeExtra(i)} style={{
                  position: 'absolute', top: 4, right: 4,
                  background: 'rgba(0,0,0,.6)', border: 'none', borderRadius: '50%',
                  width: 22, height: 22, cursor: 'pointer', color: '#fff',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 0,
                }}>
                  <Icon name="x" size={11} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
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
  const [aiSpecs, setAiSpecs]   = useState(null)
  const [tasacion, setTasacion] = useState(null)
  const [isDragging, setIsDragging] = useState(false)
  const [shotFiles, setShotFiles]         = useState({})
  const [shotPreviews, setShotPreviews]   = useState({})
  const [extraFiles, setExtraFiles]       = useState([])
  const [extraPreviews, setExtraPreviews] = useState([])
  const [vendedores, setVendedores] = useState([])
  const [form, setForm] = useState({
    tipo: 'auto', marca: '', modelo: '', anio: '', version: '',
    patente: '', color: '', km_hs: '', precio_base: '', precio_lista: '', costo_compra: '',
    combustible: '', transmision: '', origen: 'compra_directa',
    responsable_id: '',
    nro_motor: '', nro_chasis: '', notas_internas: '', estado: 'disponible',
    ubicacion: 'showroom', estado_recon: 'ingresado',
    specs: {},
  })

  useEffect(() => { getVendedores().then(setVendedores) }, [])

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
    setAiSpecs(specs)
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
    setAiLoading('specs'); setAiMsg(null); setAiSpecs(null)
    try {
      const specs = await _completarSpecs(
        form.marca, form.modelo, form.anio, form.version, form.nro_motor, form.nro_chasis
      )
      if (specs) {
        setAiMsg({ type: 'success', text: 'Especificaciones técnicas completadas por IA.' })
      }
    } catch (err) {
      setAiMsg({ type: 'warning', text: 'Error IA: ' + err.message })
    } finally { setAiLoading('') }
  }

  async function handleTasacion() {
    if (!form.marca || !form.modelo) return
    setAiLoading('precio'); setAiMsg(null); setTasacion(null)
    try {
      const data = await callAI('/ai/tasacion', {
        marca: form.marca, modelo: form.modelo, anio: Number(form.anio) || 0,
        version: form.version, km: Number(form.km_hs) || 0, estado: 'bueno',
      })
      setTasacion(data)
      setForm(p => ({ ...p, precio_base: String(data.precio_sugerido || p.precio_base) }))
      const argCtx = data.argautos_precio_usd ? ` · ArgAutos: USD ${data.argautos_precio_usd?.toLocaleString('es-AR')}` : ''
      setAiMsg({ type: 'success', text: `Tasación: USD ${data.precio_sugerido?.toLocaleString('es-AR')} (${data.precio_min?.toLocaleString('es-AR')} – ${data.precio_max?.toLocaleString('es-AR')}) · confianza: ${data.confianza}${argCtx}` })
    } catch (err) {
      setAiMsg({ type: 'warning', text: 'Error tasación: ' + err.message })
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
        precio_lista: form.precio_lista ? Number(form.precio_lista) : null,
        costo_compra: form.costo_compra ? Number(form.costo_compra) : null,
        patente: form.patente ? form.patente.toUpperCase() : null,
        responsable_id: form.responsable_id || null,
        specs: Object.keys(form.specs || {}).length > 0 ? form.specs : null,
      }
      const v = await createVehiculo(payload)
      // Upload shot list fotos
      for (const shot of SHOT_LIST) {
        const file = shotFiles[shot.key]
        if (!file) continue
        const esPortada = shot.key === 'frente_3_4_izq' ||
          (Object.keys(shotFiles)[0] === shot.key && !shotFiles['frente_3_4_izq'])
        const fotoData = await uploadFotoVehiculo(v.id, file, shot.key)
        await saveFotoRecord(v.id, fotoData, esPortada)
      }
      // Upload fotos adicionales
      for (let i = 0; i < extraFiles.length; i++) {
        const fotoData = await uploadFotoVehiculo(v.id, extraFiles[i], 'extra')
        await saveFotoRecord(v.id, fotoData, false)
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
            <p className="page-caption">Paso {step} de 3 — {step === 1 ? 'Datos del vehículo' : step === 2 ? 'Fotos' : 'Especificaciones'}</p>
          </div>
          <div style={{ flex: 1 }} />
          <div className="seg">
            <button className={step === 1 ? 'on' : ''} onClick={() => setStep(1)}>
              <Icon name="clipboard" size={13} /> Datos
            </button>
            <button className={step === 2 ? 'on' : ''} onClick={() => setStep(2)}>
              <Icon name="image" size={13} /> Fotos
            </button>
            <button className={step === 3 ? 'on' : ''} onClick={() => setStep(3)}>
              <Icon name="cog" size={13} /> Specs
            </button>
          </div>
        </div>

        {error && (
          <div className="banner warning">
            <Icon name="alert" size={16} />{error}
          </div>
        )}

        {step === 1 && aiConfigured() && (
          <div className="card" style={{ marginBottom: 12 }}>
            {/* Drop zone — siempre visible */}
            <div
              onDragOver={e => { e.preventDefault(); setIsDragging(true) }}
              onDragLeave={e => { if (!e.currentTarget.contains(e.relatedTarget)) setIsDragging(false) }}
              onDrop={e => {
                e.preventDefault(); setIsDragging(false)
                const imgs = Array.from(e.dataTransfer.files)
                if (imgs.length) handleCedulaFiles({ target: { files: imgs, value: '' } })
              }}
              onClick={() => document.getElementById('cedula-scan').click()}
              style={{
                border: isDragging ? '2px solid var(--c-accent)' : '2px dashed var(--c-border)',
                borderRadius: 'var(--r)',
                background: isDragging ? 'var(--c-accent-tint, rgba(99,102,241,.07))' : 'var(--c-bg-2)',
                padding: '18px 24px',
                display: 'flex', alignItems: 'center', gap: 14,
                cursor: 'pointer',
                transition: 'border-color .15s, background .15s',
                marginBottom: 12,
              }}
            >
              <Icon name="image" size={28} style={{ stroke: isDragging ? 'var(--c-accent)' : 'var(--c-fg-3)', flexShrink: 0 }} />
              <div>
                <div style={{ fontWeight: 600, fontSize: 14, color: isDragging ? 'var(--c-accent)' : 'var(--c-fg)' }}>
                  {isDragging ? 'Soltá el documento aquí' : 'Arrastrá aquí la cédula verde u otro documento'}
                </div>
                <div style={{ fontSize: 12, color: 'var(--c-fg-3)', marginTop: 2 }}>
                  También podés hacer click para seleccionar — JPG, PNG, PDF
                </div>
              </div>
              {aiLoading === 'cedula' && (
                <span style={{ marginLeft: 'auto', fontSize: 12, color: 'var(--c-accent)' }}>Escaneando…</span>
              )}
              <input id="cedula-scan" type="file" accept="image/*,application/pdf" multiple style={{ display: 'none' }}
                onChange={handleCedulaFiles} />
            </div>

            {/* Botones adicionales */}
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
              <span style={{ fontSize: 12, color: 'var(--c-fg-3)', fontWeight: 600, marginRight: 4 }}>IA</span>
              <button className="btn secondary" disabled={!!aiLoading || !form.marca || !form.modelo}
                onClick={handleCompletarSpecs} style={{ fontSize: 12 }}>
                <Icon name="cog" size={13} />
                {aiLoading === 'specs' ? 'Completando…' : 'Completar specs'}
              </button>
              <button className="btn secondary" disabled={!!aiLoading || !form.marca || !form.modelo}
                onClick={handleTasacion} style={{ fontSize: 12 }}>
                <Icon name="tag" size={13} />
                {aiLoading === 'precio' ? 'Tasando…' : 'Tasación IA'}
              </button>
            </div>

            {/* Mensajes y warnings */}
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

            {/* Panel de specs técnicas */}
            {aiSpecs && (
              <div style={{ marginTop: 12, background: 'var(--c-bg-2)', borderRadius: 'var(--r)', padding: 14, borderLeft: '3px solid var(--c-accent)' }}>
                <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--c-accent)', marginBottom: 10, textTransform: 'uppercase', letterSpacing: .5 }}>
                  Especificaciones técnicas — completado por IA
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(130px, 1fr))', gap: 10 }}>
                  {[
                    ['Potencia', aiSpecs.potencia_hp ? `${aiSpecs.potencia_hp} HP` : null],
                    ['Torque', aiSpecs.torque_nm ? `${aiSpecs.torque_nm} Nm` : null],
                    ['Cilindros', aiSpecs.cilindros ? String(aiSpecs.cilindros) : null],
                    ['Tanque', aiSpecs.tanque_litros ? `${aiSpecs.tanque_litros} L` : null],
                    ['Peso', aiSpecs.peso_kg ? `${aiSpecs.peso_kg} kg` : null],
                    ['Refrigeración', aiSpecs.refrigeracion || null],
                    ['Combustible', aiSpecs.combustible || null],
                    ['Transmisión', aiSpecs.transmision || null],
                  ].filter(([, v]) => v).map(([label, value]) => (
                    <div key={label} style={{ background: 'var(--c-bg)', borderRadius: 'var(--r)', padding: '8px 10px' }}>
                      <div style={{ fontSize: 11, color: 'var(--c-fg-3)', marginBottom: 2 }}>{label}</div>
                      <div style={{ fontSize: 13, fontWeight: 600 }}>{value}</div>
                    </div>
                  ))}
                </div>
                {aiSpecs.nota && (
                  <div className="banner info" style={{ marginTop: 10, fontSize: 12 }}>
                    <Icon name="info" size={14} />{aiSpecs.nota}
                  </div>
                )}
                {aiSpecs.destacado?.length > 0 && (
                  <div style={{ marginTop: 10 }}>
                    <div style={{ fontSize: 11, color: 'var(--c-fg-3)', marginBottom: 6 }}>★ Destacado</div>
                    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                      {aiSpecs.destacado.map((d, i) => (
                        <span key={i} style={{ fontSize: 12, background: 'var(--c-accent-tint, rgba(99,102,241,.1))', color: 'var(--c-accent)', borderRadius: 4, padding: '2px 8px' }}>
                          {d}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Panel de tasación */}
            {tasacion && (
              <div style={{ marginTop: 12, background: 'var(--c-bg-2)', borderRadius: 'var(--r)', padding: 14, borderLeft: '3px solid #22c55e' }}>
                <div style={{ fontSize: 12, fontWeight: 700, color: '#22c55e', marginBottom: 10, textTransform: 'uppercase', letterSpacing: .5 }}>
                  Tasación de mercado — IA
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10, marginBottom: 10 }}>
                  {[
                    ['Mínimo', tasacion.precio_min],
                    ['Sugerido', tasacion.precio_sugerido],
                    ['Máximo', tasacion.precio_max],
                  ].map(([label, val]) => (
                    <div key={label} style={{ background: 'var(--c-bg)', borderRadius: 'var(--r)', padding: '8px 12px', textAlign: 'center' }}>
                      <div style={{ fontSize: 11, color: 'var(--c-fg-3)' }}>{label}</div>
                      <div style={{ fontSize: 15, fontWeight: 700 }}>USD {val?.toLocaleString('es-AR')}</div>
                    </div>
                  ))}
                </div>
                {tasacion.argautos_precio_usd && (
                  <div style={{ fontSize: 12, color: 'var(--c-fg-2)', marginBottom: 6 }}>
                    <strong>ArgAutos:</strong> USD {tasacion.argautos_precio_usd?.toLocaleString('es-AR')}
                    {tasacion.argautos_version_exacta ? ` · ${tasacion.argautos_version_exacta}` : ''}
                  </div>
                )}
                {tasacion.razonamiento && (
                  <div style={{ fontSize: 12, color: 'var(--c-fg-2)', marginBottom: 6 }}>{tasacion.razonamiento}</div>
                )}
                {tasacion.advertencias?.length > 0 && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                    {tasacion.advertencias.map((a, i) => (
                      <div key={i} className="banner warning" style={{ marginBottom: 0, fontSize: 12 }}>
                        <Icon name="alert" size={13} />{a}
                      </div>
                    ))}
                  </div>
                )}
                <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
                  <button className="btn secondary" style={{ fontSize: 12 }}
                    onClick={() => setForm(p => ({ ...p, precio_base: String(tasacion.precio_sugerido) }))}>
                    Usar precio sugerido
                  </button>
                  <button className="btn ghost" style={{ fontSize: 12 }}
                    onClick={() => setForm(p => ({ ...p, precio_base: String(tasacion.precio_min) }))}>
                    Usar mínimo
                  </button>
                  <button className="btn ghost" style={{ fontSize: 12 }}
                    onClick={() => setForm(p => ({ ...p, precio_base: String(tasacion.precio_max) }))}>
                    Usar máximo
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        <div className="card" style={{ marginBottom: 20 }}>
          {step === 1 && <Step1 form={form} set={setForm} vendedores={vendedores} />}
          {step === 2 && <Step2 shotFiles={shotFiles} setShotFiles={setShotFiles} shotPreviews={shotPreviews} setShotPreviews={setShotPreviews} extraFiles={extraFiles} setExtraFiles={setExtraFiles} extraPreviews={extraPreviews} setExtraPreviews={setExtraPreviews} />}
          {step === 3 && <Step3 form={form} setForm={setForm} />}
        </div>

        <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
          {step > 1 && (
            <button className="btn secondary" onClick={() => setStep(s => s - 1)}>
              <Icon name="arrow-l" size={14} /> Atrás
            </button>
          )}
          {step < 3 && (
            <button className="btn primary" onClick={() => setStep(s => s + 1)}>
              Siguiente <Icon name="chev-r" size={14} />
            </button>
          )}
          {step === 3 && (
            <button className="btn primary" onClick={handleSubmit} disabled={saving}>
              {saving ? 'Guardando…' : <><Icon name="check" size={14} /> Guardar vehículo</>}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
