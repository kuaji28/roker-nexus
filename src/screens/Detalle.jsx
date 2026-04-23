import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import TopBar from '../components/TopBar'
import StateBadge from '../components/StateBadge'
import Icon from '../components/Icon'
import Modal from '../components/Modal'
import FormField from '../components/FormField'
import { getVehiculo, updateVehiculo } from '../lib/supabase'

const TC = 1415

export default function Detalle({ onLogout }) {
  const { id } = useParams()
  const navigate = useNavigate()
  const [data, setData]   = useState(null)
  const [tab, setTab]     = useState('info')
  const [foto, setFoto]   = useState(0)

  useEffect(() => {
    getVehiculo(id).then(setData)
  }, [id])

  if (!data) return (
    <div>
      <TopBar onLogout={onLogout} />
      <div className="main"><p style={{ color: 'var(--c-fg-2)' }}>Cargando…</p></div>
    </div>
  )

  const { vehiculo: v, medias } = data

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
      getVehiculo(id).then(setData)
    } finally {
      setSaving(false)
    }
  }

  if (!v) return (
    <div>
      <TopBar onLogout={onLogout} />
      <div className="main">
        <div className="banner warning"><Icon name="alert" size={16} />Vehículo no encontrado.</div>
      </div>
    </div>
  )

  const fotos = medias.filter(m => m.tipo === 'foto' && m.url)

  const specs = [
    ['Combustible', v.combustible],
    ['Transmisión', v.transmision],
    ['Motor / CV', v.motor_cv],
    ['Tracción', v.traccion],
    ['Puertas', v.puertas],
    ...(v.specs ? Object.entries(v.specs) : []),
  ].filter(([, val]) => val)

  return (
    <div>
      <TopBar onLogout={onLogout} />
      <div className="main">
        <a className="back-link" onClick={() => navigate('/catalogo')}>
          <Icon name="arrow-l" size={14} /> Volver al catálogo
        </a>

        <div className="page-head">
          <div>
            <h1 className="page-title">{v.marca} {v.modelo} {v.anio}</h1>
            <p className="page-caption">
              {v.version && <>Versión: <strong style={{ color: 'var(--c-fg)' }}>{v.version}</strong> · </>}
              Stock <strong style={{ color: 'var(--c-fg)', fontFamily: 'var(--mono)' }}>#{v.id}</strong>
              {v.patente && <> · Patente <strong style={{ color: 'var(--c-fg)', fontFamily: 'var(--mono)' }}>{v.patente}</strong></>}
            </p>
          </div>
          <div style={{ flex: 1 }} />
          <button className="btn secondary"><Icon name="share" size={14} />Compartir</button>
          <button className="btn primary" onClick={openEdit}><Icon name="edit" size={14} />Editar</button>
        </div>

        {/* KPI row */}
        <div className="detail-head">
          <div className="dm">
            <div className="lbl">Estado</div>
            <div className="val" style={{ fontSize: 16 }}><StateBadge estado={v.estado} /></div>
          </div>
          <div className="dm">
            <div className="lbl">Kilometraje</div>
            <div className="val">
              {v.km_hs?.toLocaleString('es-AR') || '0'}
              <span style={{ fontSize: 13, color: 'var(--c-fg-2)', fontWeight: 400, marginLeft: 4 }}>km</span>
            </div>
          </div>
          <div className="dm">
            <div className="lbl">Precio</div>
            <div className="val">
              <span style={{ fontSize: 14, color: 'var(--c-fg-2)', fontWeight: 500, marginRight: 4 }}>USD</span>
              {v.precio_base?.toLocaleString('es-AR')}
            </div>
          </div>
          <div className="dm">
            <div className="lbl">ARS</div>
            <div className="val g" style={{ fontSize: 16 }}>
              $ {((v.precio_base || 0) * TC).toLocaleString('es-AR')}
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="tabs">
          {[['info','info','Información'],['fotos','image','Fotos'],['docs','doc','Documentación'],['res','users','Reservas']].map(([k, ic, l]) => (
            <button key={k} className={tab === k ? 'on' : ''} onClick={() => setTab(k)}>
              <Icon name={ic} size={13} />{l}
              {k === 'fotos' && fotos.length > 0 && <span style={{ marginLeft: 4, fontSize: 11, color: 'var(--c-fg-3)' }}>{fotos.length}</span>}
            </button>
          ))}
        </div>

        {tab === 'info' && (
          <div className="info-grid">
            <div className="card info-card">
              <h3><Icon name="cog" size={14} />Especificaciones</h3>
              {specs.length > 0
                ? specs.map(([k, val]) => (
                    <div key={k} className="kv"><span>{k}</span><span>{val}</span></div>
                  ))
                : <p style={{ color: 'var(--c-fg-3)', fontSize: 13 }}>Sin datos cargados.</p>
              }
            </div>
            <div className="card info-card">
              <h3><Icon name="clipboard" size={14} />Identificación</h3>
              <div className="kv"><span>Color</span><span>{v.color || '—'}</span></div>
              <div className="kv"><span>Patente</span><span style={{ fontFamily: 'var(--mono)' }}>{v.patente || '—'}</span></div>
              <div className="kv"><span>Tipo</span><span style={{ textTransform: 'capitalize' }}>{v.tipo}</span></div>
              {v.vin && <div className="kv"><span>VIN</span><span style={{ fontFamily: 'var(--mono)', fontSize: 11 }}>{v.vin}</span></div>}
            </div>
            <div className="card info-card">
              <h3><Icon name="tag" size={14} />Precio</h3>
              <div className="kv"><span>Precio base</span><span>USD {v.precio_base?.toLocaleString('es-AR')}</span></div>
              <div className="kv"><span>En ARS</span><span>$ {((v.precio_base || 0) * TC).toLocaleString('es-AR')}</span></div>
              {v.precio_costo && <div className="kv"><span>Costo</span><span>USD {v.precio_costo?.toLocaleString('es-AR')}</span></div>}
            </div>
          </div>
        )}

        {tab === 'fotos' && (
          fotos.length === 0
            ? <div className="banner info"><Icon name="info" size={16} />Sin fotos cargadas.</div>
            : (
              <div>
                <div style={{
                  aspectRatio: '16/9', background: 'var(--c-card-2)',
                  borderRadius: 'var(--r-lg)', overflow: 'hidden', marginBottom: 12, position: 'relative',
                }}>
                  <img src={fotos[foto].url} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                  <span style={{
                    position: 'absolute', bottom: 12, right: 12,
                    background: 'rgba(0,0,0,.6)', color: '#fff',
                    fontSize: 12, padding: '3px 10px', borderRadius: 999,
                  }}>
                    {foto + 1} / {fotos.length}
                  </span>
                  {foto > 0 && (
                    <button onClick={() => setFoto(f => f - 1)} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', background: 'rgba(0,0,0,.5)', border: 'none', borderRadius: '50%', width: 36, height: 36, cursor: 'pointer', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <Icon name="chev-l" size={18} />
                    </button>
                  )}
                  {foto < fotos.length - 1 && (
                    <button onClick={() => setFoto(f => f + 1)} style={{ position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)', background: 'rgba(0,0,0,.5)', border: 'none', borderRadius: '50%', width: 36, height: 36, cursor: 'pointer', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <Icon name="chev-r" size={18} />
                    </button>
                  )}
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(80px, 1fr))', gap: 6 }}>
                  {fotos.map((f, i) => (
                    <div key={i} onClick={() => setFoto(i)} style={{
                      aspectRatio: '4/3', borderRadius: 'var(--r-sm)', overflow: 'hidden', cursor: 'pointer',
                      border: `2px solid ${i === foto ? 'var(--c-success)' : 'transparent'}`,
                    }}>
                      <img src={f.url} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                    </div>
                  ))}
                </div>
              </div>
            )
        )}

        {tab === 'docs' && (
          <div className="banner info" style={{ marginTop: 0 }}>
            <Icon name="info" size={16} />
            Módulo de documentación próximamente.
          </div>
        )}

        {tab === 'res' && (
          <div className="banner info" style={{ marginTop: 0 }}>
            <Icon name="info" size={16} />
            Sin reservas activas.
          </div>
        )}
      </div>

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
                  <option key={e} value={e}>{e.replace('_', ' ')}</option>)}
              </select>
            </FormField>
            <FormField label="Combustible"><input className="input" value={editForm.combustible} onChange={fe('combustible')} /></FormField>
            <FormField label="Transmisión"><input className="input" value={editForm.transmision} onChange={fe('transmision')} /></FormField>
          </div>
          <div style={{ marginTop: 14 }}>
            <FormField label="Notas internas">
              <textarea className="input" rows={3} value={editForm.notas_internas} onChange={fe('notas_internas')} style={{ resize: 'vertical' }} />
            </FormField>
          </div>
          <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', marginTop: 16 }}>
            <button className="btn secondary" onClick={() => setEditing(false)}>Cancelar</button>
            <button className="btn primary" onClick={saveEdit} disabled={saving}>
              {saving ? 'Guardando…' : <><Icon name="check" size={14} /> Guardar cambios</>}
            </button>
          </div>
        </Modal>
      )}
    </div>
  )
}
