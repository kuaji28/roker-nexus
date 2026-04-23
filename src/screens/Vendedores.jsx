import { useEffect, useState } from 'react'
import TopBar from '../components/TopBar'
import Modal from '../components/Modal'
import FormField from '../components/FormField'
import Icon from '../components/Icon'
import { getVendedores, createVendedor, updateVendedor } from '../lib/supabase'

export default function Vendedores({ onLogout }) {
  const [vendedores, setVendedores] = useState([])
  const [modal, setModal]   = useState(null) // null | 'new' | vendedorObj
  const [saving, setSaving] = useState(false)
  const [form, setForm]     = useState({ nombre: '', email: '', telefono: '', activo: true })

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
