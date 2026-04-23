import { useEffect, useState } from 'react'
import TopBar from '../components/TopBar'
import Modal from '../components/Modal'
import FormField from '../components/FormField'
import Icon from '../components/Icon'
import { getVendedores, createVendedor, updateVendedor } from '../lib/supabase'

const ROLES = ['vendedor', 'gerente', 'administrativo', 'otro']

const EMPTY = {
  nombre: '', email: '', telefono: '', whatsapp: '', dni: '',
  rol: 'vendedor', comision_pct: '', notas: '', telegram_chat_id: '', activo: true,
}

export default function Vendedores({ onLogout }) {
  const [vendedores, setVendedores] = useState([])
  const [modal, setModal]   = useState(null)
  const [saving, setSaving] = useState(false)
  const [form, setForm]     = useState(EMPTY)
  const [tab, setTab]       = useState('datos')

  function reload() { getVendedores().then(setVendedores) }
  useEffect(() => { reload() }, [])

  function openNew()  { setForm(EMPTY); setTab('datos'); setModal('new') }
  function openEdit(v) {
    setForm({
      nombre:          v.nombre         || '',
      email:           v.email          || '',
      telefono:        v.telefono       || '',
      whatsapp:        v.whatsapp       || '',
      dni:             v.dni            || '',
      rol:             v.rol            || 'vendedor',
      comision_pct:    v.comision_pct   ?? '',
      notas:           v.notas          || '',
      telegram_chat_id: v.telegram_chat_id || '',
      activo:          v.activo !== false,
    })
    setTab('datos')
    setModal(v)
  }

  const f = (k) => (e) => setForm(p => ({ ...p, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value }))

  async function save() {
    if (!form.nombre) return
    setSaving(true)
    try {
      const payload = {
        ...form,
        comision_pct: form.comision_pct !== '' ? Number(form.comision_pct) : null,
        telegram_chat_id: form.telegram_chat_id || null,
        whatsapp: form.whatsapp || null,
        dni: form.dni || null,
      }
      if (modal === 'new') await createVendedor(payload)
      else await updateVendedor(modal.id, payload)
      reload(); setModal(null)
    } finally { setSaving(false) }
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
                  <th>Rol</th>
                  <th>Teléfono / WA</th>
                  <th>Email</th>
                  <th className="num">Comisión</th>
                  <th>Estado</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {vendedores.map(v => (
                  <tr key={v.id}>
                    <td>
                      <strong>{v.nombre}</strong>
                      {v.dni && <div style={{ fontSize: 11, color: 'var(--c-fg-2)' }}>DNI {v.dni}</div>}
                    </td>
                    <td style={{ color: 'var(--c-fg-2)', fontSize: 12, textTransform: 'capitalize' }}>{v.rol || 'vendedor'}</td>
                    <td style={{ color: 'var(--c-fg-2)', fontSize: 12 }}>
                      {v.telefono || '—'}
                      {v.whatsapp && v.whatsapp !== v.telefono && (
                        <> · <a href={`https://wa.me/${v.whatsapp.replace(/\D/g,'')}`} target="_blank" rel="noreferrer"
                          style={{ color: 'var(--c-accent)' }}>WA</a></>
                      )}
                    </td>
                    <td style={{ color: 'var(--c-fg-2)', fontSize: 12 }}>{v.email || '—'}</td>
                    <td className="num" style={{ fontSize: 12 }}>
                      {v.comision_pct != null ? `${v.comision_pct}%` : '—'}
                    </td>
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
        <Modal title={modal === 'new' ? 'Nuevo vendedor' : `Editar — ${form.nombre}`} onClose={() => setModal(null)}>
          <div className="tabs" style={{ marginBottom: 16 }}>
            {[['datos','Datos'], ['config','Configuración']].map(([k,l]) => (
              <button key={k} className={tab === k ? 'on' : ''} onClick={() => setTab(k)}>{l}</button>
            ))}
          </div>

          {tab === 'datos' ? (
            <div style={{ display: 'grid', gap: 14 }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <FormField label="Nombre" required>
                  <input className="input" value={form.nombre} onChange={f('nombre')} placeholder="Juan García" />
                </FormField>
                <FormField label="DNI">
                  <input className="input" value={form.dni} onChange={f('dni')} placeholder="12345678" />
                </FormField>
                <FormField label="Email">
                  <input className="input" type="email" value={form.email} onChange={f('email')} placeholder="juan@ghcars.com" />
                </FormField>
                <FormField label="Rol">
                  <select className="input" value={form.rol} onChange={f('rol')}>
                    {ROLES.map(r => <option key={r} value={r}>{r}</option>)}
                  </select>
                </FormField>
                <FormField label="Teléfono">
                  <input className="input" value={form.telefono} onChange={f('telefono')} placeholder="+54 9 11 ..." />
                </FormField>
                <FormField label="WhatsApp">
                  <input className="input" value={form.whatsapp} onChange={f('whatsapp')} placeholder="+54 9 11 ..." />
                </FormField>
                <FormField label="Comisión %">
                  <input className="input" type="number" min="0" max="100" step="0.5"
                    value={form.comision_pct} onChange={f('comision_pct')} placeholder="3" />
                </FormField>
              </div>
              <FormField label="Notas">
                <textarea className="input" rows={2} value={form.notas} onChange={f('notas')} style={{ resize: 'vertical' }} />
              </FormField>
              <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', fontSize: 13 }}>
                <input type="checkbox" checked={form.activo} onChange={f('activo')} />
                Vendedor activo
              </label>
            </div>
          ) : (
            <div style={{ display: 'grid', gap: 14 }}>
              <FormField label="Telegram Chat ID">
                <input className="input" value={form.telegram_chat_id} onChange={f('telegram_chat_id')}
                  placeholder="Ej: 5427210648" />
              </FormField>
              <div className="banner info" style={{ fontSize: 12 }}>
                <Icon name="info" size={14} />
                <div>
                  <strong>¿Cómo obtener el Chat ID?</strong><br />
                  1. Abrí Telegram y buscá <strong>@RawDataBot</strong><br />
                  2. Enviá cualquier mensaje<br />
                  3. Copiá el número que dice <code>id</code> en "chat"<br />
                  4. Pegalo arriba — el bot enviará notificaciones a ese chat
                </div>
              </div>
            </div>
          )}

          <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', marginTop: 20 }}>
            <button className="btn secondary" onClick={() => setModal(null)}>Cancelar</button>
            <button className="btn primary" onClick={save} disabled={saving || !form.nombre}>
              {saving ? 'Guardando…' : <><Icon name="check" size={14} /> Guardar</>}
            </button>
          </div>
        </Modal>
      )}
    </div>
  )
}
