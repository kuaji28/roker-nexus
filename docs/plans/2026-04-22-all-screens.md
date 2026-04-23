# GH Cars — All Screens Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build all 8 remaining screens + Edit mode in Detalle so GH Cars web app is fully operational.

**Architecture:** Each screen is a self-contained JSX file in `src/screens/`. Shared data logic lives in `src/lib/supabase.js`. Shared UI components in `src/components/`. One new shared component (Modal) used by Ingreso and Edit. No new npm deps — charts done with inline SVG.

**Tech Stack:** React 18, React Router v6, @supabase/supabase-js v2, Supabase Storage (bucket `vehiculos-fotos`), CSS design system (shell.css already loaded)

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `src/lib/supabase.js` | Modify | Add 12 new helper functions |
| `src/components/Modal.jsx` | Create | Reusable modal overlay |
| `src/components/FormField.jsx` | Create | Labeled input/select/textarea wrapper |
| `src/screens/Ingreso.jsx` | Replace Placeholder | Multi-step form: datos + fotos |
| `src/screens/Ventas.jsx` | Replace Placeholder | Select vehicle → buyer → payment → confirm |
| `src/screens/Reportes.jsx` | Replace Placeholder | KPIs mes actual + SVG bar chart |
| `src/screens/Gerente.jsx` | Replace Placeholder | Advanced dashboard: pipeline + ranking |
| `src/screens/Vendedores.jsx` | Replace Placeholder | List + add/edit seller modal |
| `src/screens/Cobranza.jsx` | Replace Placeholder | Financing list + overdue cuotas |
| `src/screens/Config.jsx` | Replace Placeholder | PIN change + TC manual |
| `src/screens/Detalle.jsx` | Modify | Wire Edit button to edit modal |

---

## Task 1: Supabase Storage bucket + data helpers

**Files:**
- Modify: `src/lib/supabase.js`
- Create bucket via SQL (run once)

- [ ] **Step 1: Create Storage bucket in Supabase**

Run this SQL in Supabase SQL Editor (project `zjrabazzvckvxhufppoa`):
```sql
INSERT INTO storage.buckets (id, name, public)
VALUES ('vehiculos-fotos', 'vehiculos-fotos', true)
ON CONFLICT (id) DO NOTHING;

CREATE POLICY "anon upload vehiculos-fotos"
ON storage.objects FOR INSERT TO anon
WITH CHECK (bucket_id = 'vehiculos-fotos');

CREATE POLICY "anon read vehiculos-fotos"
ON storage.objects FOR SELECT TO anon
USING (bucket_id = 'vehiculos-fotos');
```

- [ ] **Step 2: Add all data helpers to `src/lib/supabase.js`**

Append to the existing file:

```js
// ── Vehiculos CRUD ───────────────────────────────────────────────
export async function createVehiculo(data) {
  const { data: v, error } = await supabase
    .from('vehiculos')
    .insert([{ ...data, estado: data.estado || 'disponible', fecha_ingreso: new Date().toISOString().split('T')[0] }])
    .select()
    .single()
  if (error) throw error
  return v
}

export async function updateVehiculo(id, data) {
  const { error } = await supabase
    .from('vehiculos')
    .update({ ...data, updated_at: new Date().toISOString() })
    .eq('id', id)
  if (error) throw error
}

// ── Fotos ────────────────────────────────────────────────────────
export async function uploadFoto(vehiculoId, file) {
  const path = `${vehiculoId}/${Date.now()}-${file.name.replace(/\s+/g, '_')}`
  const { data, error } = await supabase.storage
    .from('vehiculos-fotos')
    .upload(path, file, { contentType: file.type, upsert: false })
  if (error) throw error
  const { data: { publicUrl } } = supabase.storage
    .from('vehiculos-fotos')
    .getPublicUrl(data.path)
  // Save to medias table
  await supabase.from('medias').insert([{
    vehiculo_id: vehiculoId, tipo: 'foto', url: publicUrl,
    orden: 0
  }])
  return publicUrl
}

export async function deleteFoto(mediaId, storagePath) {
  if (storagePath) {
    await supabase.storage.from('vehiculos-fotos').remove([storagePath])
  }
  await supabase.from('medias').delete().eq('id', mediaId)
}

// ── Vendedores ───────────────────────────────────────────────────
export async function getVendedores() {
  const { data } = await supabase
    .from('vendedores')
    .select('id, nombre, email, telefono, activo, created_at')
    .order('nombre')
  return data || []
}

export async function createVendedor(data) {
  const { error } = await supabase.from('vendedores').insert([data])
  if (error) throw error
}

export async function updateVendedor(id, data) {
  const { error } = await supabase.from('vendedores').update(data).eq('id', id)
  if (error) throw error
}

// ── Ventas ───────────────────────────────────────────────────────
export async function getVentas() {
  const { data } = await supabase
    .from('con_ventas')
    .select('*, vehiculos(marca, modelo, anio, patente), vendedores(nombre)')
    .order('fecha_venta', { ascending: false })
    .limit(100)
  return data || []
}

export async function createVenta(venta) {
  const { data, error } = await supabase
    .from('con_ventas')
    .insert([{ ...venta, fecha_venta: new Date().toISOString().split('T')[0] }])
    .select()
    .single()
  if (error) throw error
  // Update vehicle status
  await updateVehiculo(venta.vehiculo_id, { estado: 'vendido' })
  return data
}

// ── Reportes ─────────────────────────────────────────────────────
export async function getReportes() {
  const now = new Date()
  const firstDay = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().split('T')[0]

  const [{ data: ventas }, { data: todos }, { data: prospectos }] = await Promise.all([
    supabase.from('con_ventas').select('precio_final, fecha_venta, moneda_precio')
      .gte('fecha_venta', firstDay),
    supabase.from('vehiculos').select('estado, precio_base, costo_compra, fecha_ingreso'),
    supabase.from('prospectos').select('estado, created_at').gte('created_at', firstDay),
  ])

  const ventasMes  = (ventas || []).length
  const ingresoUSD = (ventas || []).reduce((s, v) => s + (Number(v.precio_final) || 0), 0)
  const disponibles = (todos || []).filter(v => v.estado === 'disponible')
  const stockUSD   = disponibles.reduce((s, v) => s + (Number(v.precio_base) || 0), 0)
  const ingresosMes = (todos || []).filter(v => v.fecha_ingreso >= firstDay).length
  const leadsNuevos = (prospectos || []).length

  // Last 6 months for bar chart
  const months = []
  for (let i = 5; i >= 0; i--) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1)
    months.push({
      label: d.toLocaleDateString('es-AR', { month: 'short' }),
      from: d.toISOString().split('T')[0],
      to: new Date(d.getFullYear(), d.getMonth() + 1, 0).toISOString().split('T')[0],
    })
  }

  const { data: hist } = await supabase
    .from('con_ventas')
    .select('fecha_venta, precio_final')
    .gte('fecha_venta', months[0].from)

  const bars = months.map(m => ({
    label: m.label,
    count: (hist || []).filter(v => v.fecha_venta >= m.from && v.fecha_venta <= m.to).length,
    total: (hist || []).filter(v => v.fecha_venta >= m.from && v.fecha_venta <= m.to)
      .reduce((s, v) => s + (Number(v.precio_final) || 0), 0),
  }))

  return { ventasMes, ingresoUSD, stockUSD, ingresosMes, leadsNuevos, bars }
}

// ── Config ───────────────────────────────────────────────────────
export async function updatePin(newPin) {
  const { error } = await supabase
    .from('config')
    .update({ valor: JSON.stringify({ pin: newPin, min_length: 4, max_length: 20 }) })
    .eq('clave', 'pin_requirement')
  if (error) throw error
}

export async function getTC() {
  const { data } = await supabase
    .from('config')
    .select('valor')
    .eq('clave', 'tipo_cambio')
    .single()
  if (data) {
    try { return Number(JSON.parse(data.valor)?.valor) || 1415 } catch { return 1415 }
  }
  return 1415
}

export async function updateTC(valor) {
  const { error } = await supabase
    .from('config')
    .upsert({ clave: 'tipo_cambio', valor: JSON.stringify({ valor }) }, { onConflict: 'clave' })
  if (error) throw error
}

// ── Cobranza ─────────────────────────────────────────────────────
export async function getFinanciamientos() {
  const { data } = await supabase
    .from('financiamientos')
    .select('*, vehiculos(marca, modelo, anio)')
    .order('created_at', { ascending: false })
  return data || []
}

export async function getCuotasVencidas() {
  const hoy = new Date().toISOString().split('T')[0]
  const { data } = await supabase
    .from('cuotas')
    .select('*, financiamientos(deudor_nombre, vehiculos(marca, modelo, anio))')
    .lt('fecha_vencimiento', hoy)
    .eq('estado', 'pendiente')
    .order('fecha_vencimiento')
  return data || []
}
```

- [ ] **Step 3: Verify no syntax errors**
```bash
cd C:\Users\kuaji\Documents\roker_nexus\sistemas\concesionaria\gh-cars-web
npm run build 2>&1 | head -30
```
Expected: No errors (or only "missing file" warnings for screens not yet built).

- [ ] **Step 4: Commit**
```bash
git -C "C:\Users\kuaji\Documents\roker_nexus\sistemas\concesionaria\gh-cars-web" add src/lib/supabase.js
git -C "C:\Users\kuaji\Documents\roker_nexus\sistemas\concesionaria\gh-cars-web" commit -m "feat: add all supabase helpers + storage bucket config"
```

---

## Task 2: Modal + FormField shared components

**Files:**
- Create: `src/components/Modal.jsx`
- Create: `src/components/FormField.jsx`

- [ ] **Step 1: Create `src/components/Modal.jsx`**

```jsx
import Icon from './Icon'

export default function Modal({ title, onClose, children, wide }) {
  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,.6)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      zIndex: 1000, padding: 16,
    }} onClick={e => e.target === e.currentTarget && onClose()}>
      <div style={{
        background: 'var(--c-card)', border: '1px solid var(--c-border)',
        borderRadius: 'var(--r-lg)', width: '100%',
        maxWidth: wide ? 860 : 560, maxHeight: '90vh',
        overflow: 'auto', padding: 24,
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700 }}>{title}</h2>
          <button onClick={onClose} className="btn ghost" style={{ padding: '6px 8px' }}>
            <Icon name="x" size={16} />
          </button>
        </div>
        {children}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Create `src/components/FormField.jsx`**

```jsx
export default function FormField({ label, required, children, hint }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <label style={{ fontSize: 11, fontWeight: 600, color: 'var(--c-fg-3)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
        {label}{required && <span style={{ color: 'var(--c-danger)', marginLeft: 2 }}>*</span>}
      </label>
      {children}
      {hint && <span style={{ fontSize: 11, color: 'var(--c-fg-3)' }}>{hint}</span>}
    </div>
  )
}
```

- [ ] **Step 3: Commit**
```bash
git -C "C:\Users\kuaji\Documents\roker_nexus\sistemas\concesionaria\gh-cars-web" add src/components/Modal.jsx src/components/FormField.jsx
git -C "C:\Users\kuaji\Documents\roker_nexus\sistemas\concesionaria\gh-cars-web" commit -m "feat: add Modal and FormField shared components"
```

---

## Task 3: Ingreso screen (add vehicle + photos)

**Files:**
- Replace: `src/screens/Ingreso.jsx`

The form has 2 steps: Step 1 = vehicle data, Step 2 = photos.

- [ ] **Step 1: Write `src/screens/Ingreso.jsx`**

```jsx
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
      <FormField label="Notas internas" style={{ gridColumn: '1 / -1' }}>
        <textarea className="input" rows={3} placeholder="Observaciones, detalles del vehículo..."
          value={form.notas_internas} onChange={f('notas_internas')}
          style={{ resize: 'vertical' }} />
      </FormField>
    </div>
  )
}

function Step2({ files, setFiles, previews, setPreviews }) {
  function handleDrop(e) {
    e.preventDefault()
    const dropped = Array.from(e.dataTransfer?.files || e.target.files || [])
      .filter(f => f.type.startsWith('image/'))
    setFiles(p => [...p, ...dropped])
    dropped.forEach(f => {
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
        onDrop={handleDrop} onDragOver={e => e.preventDefault()}
        onClick={() => document.getElementById('foto-input').click()}
        style={{
          border: '2px dashed var(--c-border)', borderRadius: 'var(--r-lg)',
          padding: 40, textAlign: 'center', cursor: 'pointer',
          color: 'var(--c-fg-2)', marginBottom: 16,
          transition: 'border-color .12s',
        }}
        onMouseEnter={e => e.currentTarget.style.borderColor = 'var(--c-success)'}
        onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--c-border)'}
      >
        <Icon name="image" size={32} style={{ stroke: 'var(--c-fg-3)', marginBottom: 8, display: 'block', margin: '0 auto 8px' }} />
        <div style={{ fontWeight: 600, marginBottom: 4 }}>Arrastrá fotos o hacé click</div>
        <div style={{ fontSize: 12, color: 'var(--c-fg-3)' }}>JPG, PNG, WEBP — múltiples archivos</div>
        <input id="foto-input" type="file" accept="image/*" multiple style={{ display: 'none' }} onChange={handleDrop} />
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
```

- [ ] **Step 2: Update App.jsx to import Ingreso**

In `src/App.jsx`, replace:
```jsx
import Placeholder from './screens/Placeholder'
```
with:
```jsx
import Placeholder from './screens/Placeholder'
import IngresoScreen from './screens/Ingreso'
```
And replace the route:
```jsx
<Route path="/ingreso"    element={<Placeholder title="Ingresar vehículo" onLogout={onLogout} />} />
```
with:
```jsx
<Route path="/ingreso"    element={<IngresoScreen onLogout={onLogout} />} />
```

- [ ] **Step 3: Verify in browser**

Navigate to `http://localhost:5173/ingreso`. Fill marca=Toyota, modelo=Corolla, anio=2020, precio_base=18000. Click Siguiente. Drop a photo. Click Guardar. Should redirect to `/vehiculo/[id]`.

- [ ] **Step 4: Commit**
```bash
git -C "C:\Users\kuaji\Documents\roker_nexus\sistemas\concesionaria\gh-cars-web" add src/screens/Ingreso.jsx src/App.jsx
git -C "C:\Users\kuaji\Documents\roker_nexus\sistemas\concesionaria\gh-cars-web" commit -m "feat: Ingreso screen — vehicle form + photo upload"
```

---

## Task 4: Ventas screen

**Files:**
- Replace: `src/screens/Ventas.jsx`

3-step flow: select vehicle → buyer info → confirm.

- [ ] **Step 1: Write `src/screens/Ventas.jsx`**

```jsx
import { useEffect, useState } from 'react'
import TopBar from '../components/TopBar'
import StateBadge from '../components/StateBadge'
import Icon from '../components/Icon'
import FormField from '../components/FormField'
import { getVehiculos, getVendedores, createVenta } from '../lib/supabase'

const TC = 1415
const FORMAS = ['Efectivo', 'Transferencia', 'Efectivo + Transferencia', 'Financiación', 'Parte de pago']

export default function Ventas({ onLogout }) {
  const [step, setStep]     = useState(1)
  const [vehiculos, setVehiculos] = useState([])
  const [vendedores, setVendedores] = useState([])
  const [selected, setSelected] = useState(null)
  const [saving, setSaving] = useState(false)
  const [done, setDone]     = useState(null)
  const [error, setError]   = useState('')
  const [buyer, setBuyer]   = useState({
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
          <button className="btn secondary" onClick={() => { setStep(1); setSelected(null); setBuyer({ comprador_nombre: '', comprador_dni: '', comprador_telefono: '', precio_final: '', moneda_precio: 'USD', forma_pago: 'Efectivo', vendedor_id: '', notas: '' }); setDone(null) }}>
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
            <button className={step === 1 ? 'on' : ''} onClick={() => step > 1 && setStep(1)}><Icon name="car" size={13} /> Vehículo</button>
            <button className={step === 2 ? 'on' : ''} disabled={!selected}><Icon name="users" size={13} /> Comprador</button>
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
                    {FORMAS.map(f => <option key={f} value={f}>{f}</option>)}
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
                    {vendedores.map(v => <option key={v.id} value={v.id}>{v.nombre}</option>)}
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
```

- [ ] **Step 2: Wire up in App.jsx**

Import and replace route:
```jsx
import VentasScreen from './screens/Ventas'
// ...
<Route path="/ventas" element={<VentasScreen onLogout={onLogout} />} />
```

- [ ] **Step 3: Commit**
```bash
git -C "C:\Users\kuaji\Documents\roker_nexus\sistemas\concesionaria\gh-cars-web" add src/screens/Ventas.jsx src/App.jsx
git -C "C:\Users\kuaji\Documents\roker_nexus\sistemas\concesionaria\gh-cars-web" commit -m "feat: Ventas screen — 3-step sale registration"
```

---

## Task 5: Reportes screen (SVG charts)

**Files:**
- Replace: `src/screens/Reportes.jsx`

- [ ] **Step 1: Write `src/screens/Reportes.jsx`**

```jsx
import { useEffect, useState } from 'react'
import TopBar from '../components/TopBar'
import MetricCard from '../components/MetricCard'
import Icon from '../components/Icon'
import { getReportes } from '../lib/supabase'

const TC = 1415

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
  const [data, setData]   = useState(null)
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
              <MetricCard label="Ventas del mes"  icon="cash"  value={data.ventasMes}   tone="g" sub="vehículos vendidos" />
              <MetricCard label="Ingreso USD"      icon="chart" value={`USD ${data.ingresoUSD.toLocaleString('es-AR')}`} tone="g" />
              <MetricCard label="Stock disponible" icon="car"   value={`USD ${data.stockUSD.toLocaleString('es-AR')}`}   tone="b" sub="valor en stock" />
              <MetricCard label="Ingresos al stock" icon="plus" value={data.ingresosMes} sub="este mes" />
              <MetricCard label="Leads nuevos"    icon="users" value={data.leadsNuevos} tone="o" />
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
```

- [ ] **Step 2: Wire up in App.jsx**
```jsx
import ReportesScreen from './screens/Reportes'
// ...
<Route path="/reportes" element={<ReportesScreen onLogout={onLogout} />} />
```

- [ ] **Step 3: Commit**
```bash
git -C "C:\Users\kuaji\Documents\roker_nexus\sistemas\concesionaria\gh-cars-web" add src/screens/Reportes.jsx src/App.jsx
git -C "C:\Users\kuaji\Documents\roker_nexus\sistemas\concesionaria\gh-cars-web" commit -m "feat: Reportes screen — KPIs + 6-month bar chart"
```

---

## Task 6: Gerente screen (advanced dashboard)

**Files:**
- Replace: `src/screens/Gerente.jsx`

- [ ] **Step 1: Write `src/screens/Gerente.jsx`**

```jsx
import { useEffect, useState } from 'react'
import TopBar from '../components/TopBar'
import Icon from '../components/Icon'
import { getStats, getVentas, getVendedores } from '../lib/supabase'

export default function Gerente({ onLogout }) {
  const [stats, setStats]       = useState(null)
  const [ventas, setVentas]     = useState([])
  const [vendedores, setVendedores] = useState([])

  useEffect(() => {
    getStats().then(setStats)
    getVentas().then(setVentas)
    getVendedores().then(setVendedores)
  }, [])

  // Build seller ranking from ventas
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
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Wire up in App.jsx**
```jsx
import GerenteScreen from './screens/Gerente'
// ...
<Route path="/gerente" element={<GerenteScreen onLogout={onLogout} />} />
```

- [ ] **Step 3: Commit**
```bash
git -C "C:\Users\kuaji\Documents\roker_nexus\sistemas\concesionaria\gh-cars-web" add src/screens/Gerente.jsx src/App.jsx
git -C "C:\Users\kuaji\Documents\roker_nexus\sistemas\concesionaria\gh-cars-web" commit -m "feat: Gerente screen — seller ranking + recent sales table"
```

---

## Task 7: Vendedores screen

**Files:**
- Replace: `src/screens/Vendedores.jsx`

- [ ] **Step 1: Check vendedores schema and write screen**

First verify: `SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'vendedores'`

Then create `src/screens/Vendedores.jsx`:

```jsx
import { useEffect, useState } from 'react'
import TopBar from '../components/TopBar'
import Modal from '../components/Modal'
import FormField from '../components/FormField'
import Icon from '../components/Icon'
import { getVendedores, createVendedor, updateVendedor } from '../lib/supabase'

export default function Vendedores({ onLogout }) {
  const [vendedores, setVendedores] = useState([])
  const [modal, setModal] = useState(null) // null | 'new' | vendedorObj
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState({ nombre: '', email: '', telefono: '', activo: true })

  function reload() { getVendedores().then(setVendedores) }
  useEffect(() => { reload() }, [])

  function openNew() { setForm({ nombre: '', email: '', telefono: '', activo: true }); setModal('new') }
  function openEdit(v) { setForm({ nombre: v.nombre, email: v.email || '', telefono: v.telefono || '', activo: v.activo !== false }); setModal(v) }

  const f = (k) => (e) => setForm(p => ({ ...p, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value }))

  async function save() {
    if (!form.nombre) return
    setSaving(true)
    try {
      if (modal === 'new') {
        await createVendedor(form)
      } else {
        await updateVendedor(modal.id, form)
      }
      reload()
      setModal(null)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      <TopBar onLogout={onLogout} />
      <div className="main">
        <div className="page-head">
          <div>
            <h1 className="page-title">Vendedores</h1>
            <p className="page-caption">{vendedores.length} en sistema</p>
          </div>
          <div style={{ flex: 1 }} />
          <button className="btn primary" onClick={openNew}>
            <Icon name="plus" size={14} /> Agregar vendedor
          </button>
        </div>

        {vendedores.length === 0
          ? <div className="banner info"><Icon name="info" size={16} />No hay vendedores registrados.</div>
          : (
            <table className="rank">
              <thead>
                <tr>
                  <th>Nombre</th>
                  <th>Email</th>
                  <th>Teléfono</th>
                  <th>Estado</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {vendedores.map(v => (
                  <tr key={v.id}>
                    <td><strong>{v.nombre}</strong></td>
                    <td style={{ color: 'var(--c-fg-2)' }}>{v.email || '—'}</td>
                    <td style={{ color: 'var(--c-fg-2)' }}>{v.telefono || '—'}</td>
                    <td>
                      <span className={`badge ${v.activo !== false ? 'success' : 'neutral'}`}>
                        <span className="cdot" /> {v.activo !== false ? 'Activo' : 'Inactivo'}
                      </span>
                    </td>
                    <td>
                      <button className="btn ghost" onClick={() => openEdit(v)}>
                        <Icon name="edit" size={14} /> Editar
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )
        }
      </div>

      {modal && (
        <Modal title={modal === 'new' ? 'Nuevo vendedor' : 'Editar vendedor'} onClose={() => setModal(null)}>
          <div style={{ display: 'grid', gap: 14 }}>
            <FormField label="Nombre" required>
              <input className="input" value={form.nombre} onChange={f('nombre')} placeholder="Juan García" />
            </FormField>
            <FormField label="Email">
              <input className="input" type="email" value={form.email} onChange={f('email')} placeholder="juan@ghcars.com" />
            </FormField>
            <FormField label="Teléfono">
              <input className="input" value={form.telefono} onChange={f('telefono')} placeholder="+54 9 11 ..." />
            </FormField>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', fontSize: 13 }}>
              <input type="checkbox" checked={form.activo} onChange={f('activo')} />
              Vendedor activo
            </label>
            <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', marginTop: 8 }}>
              <button className="btn secondary" onClick={() => setModal(null)}>Cancelar</button>
              <button className="btn primary" onClick={save} disabled={saving || !form.nombre}>
                {saving ? 'Guardando…' : <><Icon name="check" size={14} /> Guardar</>}
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Add RLS policies for vendedores**
```sql
CREATE POLICY "anon can read vendedores" ON vendedores FOR SELECT TO anon USING (true);
CREATE POLICY "anon can insert vendedores" ON vendedores FOR INSERT TO anon WITH CHECK (true);
CREATE POLICY "anon can update vendedores" ON vendedores FOR UPDATE TO anon USING (true);
```

- [ ] **Step 3: Wire up in App.jsx**
```jsx
import VendedoresScreen from './screens/Vendedores'
// ...
<Route path="/vendedores" element={<VendedoresScreen onLogout={onLogout} />} />
```

- [ ] **Step 4: Commit**
```bash
git -C "C:\Users\kuaji\Documents\roker_nexus\sistemas\concesionaria\gh-cars-web" add src/screens/Vendedores.jsx src/App.jsx
git -C "C:\Users\kuaji\Documents\roker_nexus\sistemas\concesionaria\gh-cars-web" commit -m "feat: Vendedores screen — list + add/edit modal"
```

---

## Task 8: Cobranza screen

**Files:**
- Replace: `src/screens/Cobranza.jsx`

- [ ] **Step 1: Check financiamientos + cuotas schemas**
```sql
SELECT column_name, data_type FROM information_schema.columns WHERE table_name IN ('financiamientos','cuotas') ORDER BY table_name, ordinal_position;
```

- [ ] **Step 2: Write `src/screens/Cobranza.jsx`**

```jsx
import { useEffect, useState } from 'react'
import TopBar from '../components/TopBar'
import Icon from '../components/Icon'
import { getFinanciamientos, getCuotasVencidas } from '../lib/supabase'

export default function Cobranza({ onLogout }) {
  const [finan, setFinan]   = useState([])
  const [cuotas, setCuotas] = useState([])
  const [tab, setTab]       = useState('vencidas')
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
          {[['vencidas','alert','Vencidas'], ['todos','briefcase','Todos']].map(([k,ic,l]) => (
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
                  {finan.map(f => (
                    <tr key={f.id}>
                      <td><strong>{f.deudor_nombre || '—'}</strong></td>
                      <td style={{ color: 'var(--c-fg-2)', fontSize: 12 }}>
                        {f.vehiculos?.marca} {f.vehiculos?.modelo} {f.vehiculos?.anio}
                      </td>
                      <td className="num">$ {Number(f.monto_total || 0).toLocaleString('es-AR')}</td>
                      <td style={{ color: 'var(--c-fg-2)', fontSize: 12 }}>{f.cantidad_cuotas || '—'}</td>
                      <td>
                        <span className={`badge ${f.estado === 'activo' ? 'success' : f.estado === 'vencido' ? 'danger' : 'neutral'}`}>
                          <span className="cdot" /> {f.estado || 'activo'}
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
```

- [ ] **Step 3: Add RLS for financiamientos + cuotas**
```sql
CREATE POLICY "anon can read financiamientos" ON financiamientos FOR SELECT TO anon USING (true);
CREATE POLICY "anon can read cuotas" ON cuotas FOR SELECT TO anon USING (true);
```

- [ ] **Step 4: Wire up + commit**
```jsx
import CobranzaScreen from './screens/Cobranza'
// ...
<Route path="/cobranza" element={<CobranzaScreen onLogout={onLogout} />} />
```
```bash
git -C "C:\Users\kuaji\Documents\roker_nexus\sistemas\concesionaria\gh-cars-web" add src/screens/Cobranza.jsx src/App.jsx
git -C "C:\Users\kuaji\Documents\roker_nexus\sistemas\concesionaria\gh-cars-web" commit -m "feat: Cobranza screen — overdue cuotas + financing list"
```

---

## Task 9: Config screen

**Files:**
- Replace: `src/screens/Config.jsx`

- [ ] **Step 1: Write `src/screens/Config.jsx`**

```jsx
import { useState } from 'react'
import TopBar from '../components/TopBar'
import Icon from '../components/Icon'
import FormField from '../components/FormField'
import { updatePin, getTC, updateTC } from '../lib/supabase'
import { useEffect } from 'react'

export default function Config({ onLogout }) {
  const [pin, setPin]       = useState({ current: '', new1: '', new2: '' })
  const [pinMsg, setPinMsg] = useState(null)
  const [tc, setTc]         = useState('')
  const [tcMsg, setTcMsg]   = useState(null)
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
      setPin({ current: '', new1: '', new2: '' })
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
          <h3><Icon name="key" size={14} />Cambiar PIN de acceso</h3>
          <div style={{ display: 'grid', gap: 12 }}>
            <FormField label="PIN nuevo">
              <input className="input" type="password" placeholder="····" value={pin.new1} onChange={fp('new1')} maxLength={20} />
            </FormField>
            <FormField label="Confirmar PIN">
              <input className="input" type="password" placeholder="····" value={pin.new2} onChange={fp('new2')} maxLength={20} />
            </FormField>
            {pinMsg && <div className={`banner ${pinMsg.type}`}><Icon name={pinMsg.type === 'success' ? 'check' : 'alert'} size={16} />{pinMsg.text}</div>}
            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <button className="btn primary" onClick={changePin} disabled={savingPin}>
                {savingPin ? 'Guardando…' : <><Icon name="check" size={14} /> Guardar PIN</>}
              </button>
            </div>
          </div>
        </div>

        <div className="card">
          <h3><Icon name="cash" size={14} />Tipo de cambio USD/ARS</h3>
          <div style={{ display: 'grid', gap: 12 }}>
            <FormField label="$ ARS por 1 USD" hint="Se usa para mostrar precios en pesos en toda la app">
              <input className="input" type="number" value={tc} onChange={e => setTc(e.target.value)} placeholder="1415" min={1} />
            </FormField>
            {tcMsg && <div className={`banner ${tcMsg.type}`}><Icon name={tcMsg.type === 'success' ? 'check' : 'alert'} size={16} />{tcMsg.text}</div>}
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
```

- [ ] **Step 2: Add config upsert policy**
```sql
CREATE POLICY "anon can update config" ON config FOR UPDATE TO anon USING (true);
CREATE POLICY "anon can insert config" ON config FOR INSERT TO anon WITH CHECK (true);
```

- [ ] **Step 3: Wire up + commit**
```jsx
import ConfigScreen from './screens/Config'
// ...
<Route path="/config" element={<ConfigScreen onLogout={onLogout} />} />
```
```bash
git -C "C:\Users\kuaji\Documents\roker_nexus\sistemas\concesionaria\gh-cars-web" add src/screens/Config.jsx src/App.jsx
git -C "C:\Users\kuaji\Documents\roker_nexus\sistemas\concesionaria\gh-cars-web" commit -m "feat: Config screen — PIN change + TC management"
```

---

## Task 10: Edit vehicle in Detalle

**Files:**
- Modify: `src/screens/Detalle.jsx`

The Edit button currently does nothing. Wire it to open an edit modal.

- [ ] **Step 1: Add `updateVehiculo` import + modal state to Detalle.jsx**

At top of `Detalle.jsx` add imports:
```jsx
import Modal from '../components/Modal'
import FormField from '../components/FormField'
import { updateVehiculo } from '../lib/supabase'
```

- [ ] **Step 2: Add edit state inside the component (after existing useState hooks)**

```jsx
const [editing, setEditing] = useState(false)
const [editForm, setEditForm] = useState({})
const [saving, setSaving] = useState(false)

function openEdit() {
  setEditForm({
    marca: v.marca, modelo: v.modelo, anio: v.anio,
    version: v.version || '', color: v.color || '',
    km_hs: v.km_hs || '', precio_base: v.precio_base || '',
    costo_compra: v.costo_compra || '', estado: v.estado,
    combustible: v.combustible || '', transmision: v.transmision || '',
    patente: v.patente || '', notas_internas: v.notas_internas || '',
  })
  setEditing(true)
}

const fe = (k) => (e) => setEditForm(p => ({ ...p, [k]: e.target.value }))

async function saveEdit() {
  setSaving(true)
  try {
    await updateVehiculo(v.id, {
      ...editForm,
      anio: Number(editForm.anio),
      km_hs: editForm.km_hs ? Number(editForm.km_hs) : null,
      precio_base: editForm.precio_base ? Number(editForm.precio_base) : null,
      costo_compra: editForm.costo_compra ? Number(editForm.costo_compra) : null,
    })
    setEditing(false)
    // Reload data
    getVehiculo(id).then(setData)
  } finally {
    setSaving(false)
  }
}
```

- [ ] **Step 3: Wire Edit button (line ~68 in Detalle.jsx)**

Replace:
```jsx
<button className="btn primary"><Icon name="edit" size={14} />Editar</button>
```
with:
```jsx
<button className="btn primary" onClick={openEdit}><Icon name="edit" size={14} />Editar</button>
```

- [ ] **Step 4: Add modal at the bottom (just before closing `</div>` of the component return)**

```jsx
{editing && (
  <Modal title="Editar vehículo" onClose={() => setEditing(false)} wide>
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
      <FormField label="Marca"><input className="input" value={editForm.marca} onChange={fe('marca')} /></FormField>
      <FormField label="Modelo"><input className="input" value={editForm.modelo} onChange={fe('modelo')} /></FormField>
      <FormField label="Año"><input className="input" type="number" value={editForm.anio} onChange={fe('anio')} /></FormField>
      <FormField label="Versión"><input className="input" value={editForm.version} onChange={fe('version')} /></FormField>
      <FormField label="Patente"><input className="input" value={editForm.patente} onChange={fe('patente')} /></FormField>
      <FormField label="Color"><input className="input" value={editForm.color} onChange={fe('color')} /></FormField>
      <FormField label="Km / Hs"><input className="input" type="number" value={editForm.km_hs} onChange={fe('km_hs')} /></FormField>
      <FormField label="Precio USD"><input className="input" type="number" value={editForm.precio_base} onChange={fe('precio_base')} /></FormField>
      <FormField label="Costo USD"><input className="input" type="number" value={editForm.costo_compra} onChange={fe('costo_compra')} /></FormField>
      <FormField label="Estado">
        <select className="input" value={editForm.estado} onChange={fe('estado')}>
          {['disponible','señado','en_revision','en_preparacion','vendido'].map(e =>
            <option key={e} value={e}>{e.replace('_',' ')}</option>)}
        </select>
      </FormField>
      <FormField label="Combustible"><input className="input" value={editForm.combustible} onChange={fe('combustible')} /></FormField>
      <FormField label="Transmisión"><input className="input" value={editForm.transmision} onChange={fe('transmision')} /></FormField>
    </div>
    <FormField label="Notas internas" style={{ marginTop: 14 }}>
      <textarea className="input" rows={3} value={editForm.notas_internas} onChange={fe('notas_internas')} style={{ resize: 'vertical' }} />
    </FormField>
    <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', marginTop: 16 }}>
      <button className="btn secondary" onClick={() => setEditing(false)}>Cancelar</button>
      <button className="btn primary" onClick={saveEdit} disabled={saving}>
        {saving ? 'Guardando…' : <><Icon name="check" size={14} /> Guardar cambios</>}
      </button>
    </div>
  </Modal>
)}
```

- [ ] **Step 5: Add RLS for vehiculos write**
```sql
CREATE POLICY "anon can insert vehiculos" ON vehiculos FOR INSERT TO anon WITH CHECK (true);
CREATE POLICY "anon can update vehiculos" ON vehiculos FOR UPDATE TO anon USING (true);
```

- [ ] **Step 6: Commit**
```bash
git -C "C:\Users\kuaji\Documents\roker_nexus\sistemas\concesionaria\gh-cars-web" add src/screens/Detalle.jsx
git -C "C:\Users\kuaji\Documents\roker_nexus\sistemas\concesionaria\gh-cars-web" commit -m "feat: Edit modal in Detalle — inline vehicle editing"
```

---

## Task 11: Final App.jsx cleanup + con_ventas RLS

The final App.jsx should import all screens. Also need write policies for con_ventas.

- [ ] **Step 1: Add RLS for con_ventas and medias**
```sql
CREATE POLICY "anon can insert con_ventas" ON con_ventas FOR INSERT TO anon WITH CHECK (true);
CREATE POLICY "anon can read con_ventas" ON con_ventas FOR SELECT TO anon USING (true);
CREATE POLICY "anon can insert medias" ON medias FOR INSERT TO anon WITH CHECK (true);
CREATE POLICY "anon can delete medias" ON medias FOR DELETE TO anon USING (true);
CREATE POLICY "anon can read prospectos" ON prospectos FOR SELECT TO anon USING (true);
```

- [ ] **Step 2: Final App.jsx — replace all Placeholders**

`src/App.jsx` final state:
```jsx
import { useState } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import Login from './screens/Login'
import Dashboard from './screens/Dashboard'
import Catalogo from './screens/Catalogo'
import Detalle from './screens/Detalle'
import Ingreso from './screens/Ingreso'
import Ventas from './screens/Ventas'
import Reportes from './screens/Reportes'
import Gerente from './screens/Gerente'
import Vendedores from './screens/Vendedores'
import Cobranza from './screens/Cobranza'
import Config from './screens/Config'
import Placeholder from './screens/Placeholder'

function AppShell({ onLogout }) {
  const tc = 1415
  return (
    <div className="app">
      <Sidebar tc={tc} />
      <div style={{ minWidth: 0, flex: 1 }}>
        <Routes>
          <Route path="/"           element={<Dashboard   onLogout={onLogout} />} />
          <Route path="/catalogo"   element={<Catalogo    onLogout={onLogout} />} />
          <Route path="/vehiculo/:id" element={<Detalle   onLogout={onLogout} />} />
          <Route path="/ingreso"    element={<Ingreso     onLogout={onLogout} />} />
          <Route path="/ventas"     element={<Ventas      onLogout={onLogout} />} />
          <Route path="/doc"        element={<Placeholder title="Documentación" onLogout={onLogout} />} />
          <Route path="/reportes"   element={<Reportes    onLogout={onLogout} />} />
          <Route path="/gerente"    element={<Gerente     onLogout={onLogout} />} />
          <Route path="/vendedores" element={<Vendedores  onLogout={onLogout} />} />
          <Route path="/cobranza"   element={<Cobranza    onLogout={onLogout} />} />
          <Route path="/config"     element={<Config      onLogout={onLogout} />} />
          <Route path="*"           element={<Navigate to="/" replace />} />
        </Routes>
      </div>
    </div>
  )
}

export default function App() {
  const [auth, setAuth] = useState(() => sessionStorage.getItem('gh_auth') === '1')
  function handleLogin()  { sessionStorage.setItem('gh_auth', '1'); setAuth(true) }
  function handleLogout() { sessionStorage.removeItem('gh_auth'); setAuth(false) }
  if (!auth) return <Login onLogin={handleLogin} />
  return (
    <BrowserRouter>
      <AppShell onLogout={handleLogout} />
    </BrowserRouter>
  )
}
```

- [ ] **Step 3: Final build check**
```bash
cd C:\Users\kuaji\Documents\roker_nexus\sistemas\concesionaria\gh-cars-web && npm run build 2>&1
```
Expected: `✓ built in Xs` with no errors.

- [ ] **Step 4: Final commit**
```bash
git -C "C:\Users\kuaji\Documents\roker_nexus\sistemas\concesionaria\gh-cars-web" add -A
git -C "C:\Users\kuaji\Documents\roker_nexus\sistemas\concesionaria\gh-cars-web" commit -m "feat: all screens complete — GH Cars web app v1.0"
```

---

## Self-Review

**Spec coverage:**
- ✅ Ingreso vehículo (form completo + fotos) → Task 3
- ✅ Ventas (registrar + cerrar estado) → Task 4
- ✅ Reportes (métricas + SVG bar chart) → Task 5
- ✅ Gerente (ranking vendedores + últimas ventas) → Task 6
- ✅ Vendedores (list + CRUD modal) → Task 7
- ✅ Cobranza (vencidas + todos) → Task 8
- ✅ Config (PIN + TC) → Task 9
- ✅ Editar vehículo (modal en Detalle) → Task 10
- ✅ RLS policies para todas las tablas → Tasks 1, 7, 8, 9, 11
- ✅ Supabase Storage bucket → Task 1

**Gaps detectados y corregidos:**
- `getVentas` necesita join con `vehiculos` y `vendedores` → incluido en helpers
- `Cobranza` necesita verificar schema de `financiamientos` antes de escribir → indicado en Task 8 Step 1
- `Config` necesita upsert policy (no solo update) para `tipo_cambio` → incluido en Task 9

**No placeholders:** todos los pasos tienen código completo.

**Type consistency:** `updateVehiculo(id, data)` usado igual en Task 1, Task 4, y Task 10. `getVendedores()` devuelve array usado igual en Tasks 6, 4, y 7.
