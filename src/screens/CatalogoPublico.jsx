import { useEffect, useState } from 'react'
import { supabase } from '../lib/supabase'

const FALLBACK_TC   = 1415
const WA_NUMBER     = '5491162692000'   // GH Cars WhatsApp

async function fetchTc() {
  try {
    const res = await fetch('https://dolarapi.com/v1/dolares/blue')
    if (!res.ok) throw new Error()
    const json = await res.json()
    const val = Number(json?.venta)
    if (!val || isNaN(val)) throw new Error()
    return val
  } catch {
    // Fallback: leer desde Supabase config
    try {
      const { data } = await supabase
        .from('config').select('valor').eq('clave', 'tipo_cambio').single()
      return Number(data?.valor) || FALLBACK_TC
    } catch {
      return FALLBACK_TC
    }
  }
}

async function getVehiculosPublicos({ tipo, anioMin, precioMax }) {
  let q = supabase
    .from('vehiculos')
    .select('id,tipo,marca,modelo,anio,version,km_hs,precio_lista,precio_base,transmision,color,combustible')
    .eq('estado', 'disponible')
    .order('created_at', { ascending: false })

  if (tipo && tipo !== 'todos') q = q.eq('tipo', tipo)
  if (anioMin) q = q.gte('anio', Number(anioMin))
  if (precioMax) q = q.lte('precio_lista', Number(precioMax))

  const { data } = await q
  return data || []
}

async function getPortadas(vehiculoIds) {
  if (!vehiculoIds.length) return {}
  const { data } = await supabase
    .from('medias')
    .select('vehiculo_id, url, orden')
    .in('vehiculo_id', vehiculoIds)
    .order('orden', { ascending: true })

  if (!data) return {}
  // Para cada vehículo tomar la primera foto (orden más bajo)
  const map = {}
  for (const m of data) {
    if (!map[m.vehiculo_id]) map[m.vehiculo_id] = m.url
  }
  return map
}

const TIPOS = ['todos', 'auto', 'moto', 'cuatriciclo', 'moto_de_agua']
const TIPOS_LABEL = { todos: 'Todos', auto: 'Autos', moto: 'Motos', cuatriciclo: 'Cuatriciclos', moto_de_agua: 'Motos de agua' }

function CardPublica({ v, foto, tc }) {
  const precioUSD = v.precio_lista || v.precio_base
  const precioARS = precioUSD && tc ? (precioUSD * tc).toLocaleString('es-AR') : null

  function abrirWhatsApp() {
    const msg = encodeURIComponent(
      `Hola! Vi el *${v.marca} ${v.modelo} ${v.anio}* en el catálogo de GH Cars.\n` +
      `¿Podría darme más información? 🚗`
    )
    window.open(`https://wa.me/${WA_NUMBER}?text=${msg}`, '_blank')
  }

  return (
    <div className="card" style={{ overflow: 'hidden', padding: 0, display: 'flex', flexDirection: 'column' }}>
      {/* Foto */}
      <div style={{ aspectRatio: '4/3', background: 'var(--c-card-2)', overflow: 'hidden', flexShrink: 0 }}>
        {foto
          ? <img src={foto} alt={`${v.marca} ${v.modelo}`} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
          : <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--c-fg-3)', fontSize: 40 }}>🚗</div>
        }
      </div>

      {/* Info */}
      <div style={{ padding: 16, display: 'flex', flexDirection: 'column', flex: 1 }}>
        <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 2 }}>
          {v.marca} {v.modelo}
          {v.version && <span style={{ fontWeight: 400, color: 'var(--c-fg-2)' }}> {v.version}</span>}
        </div>
        <div style={{ fontSize: 13, color: 'var(--c-fg-2)', marginBottom: 12 }}>
          {v.anio}
          {v.km_hs ? ` · ${Number(v.km_hs).toLocaleString('es-AR')} km` : ' · 0 KM'}
          {v.transmision ? ` · ${v.transmision}` : ''}
          {v.combustible ? ` · ${v.combustible}` : ''}
        </div>

        <div style={{ marginTop: 'auto' }}>
          <div style={{ fontSize: 22, fontWeight: 700, marginBottom: 2 }}>
            {precioUSD ? `USD ${precioUSD.toLocaleString('es-AR')}` : 'Consultar'}
          </div>
          {precioARS && (
            <div style={{ fontSize: 12, color: 'var(--c-fg-3)', marginBottom: 14 }}>
              ≈ ARS {precioARS}
            </div>
          )}
          <button
            className="btn btn-primary"
            style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}
            onClick={abrirWhatsApp}
          >
            💬 Consultar
          </button>
        </div>
      </div>
    </div>
  )
}

export default function CatalogoPublico() {
  const [vehiculos, setVehiculos] = useState([])
  const [portadas, setPortadas]   = useState({})
  const [tc, setTc]               = useState(FALLBACK_TC)
  const [loading, setLoading]     = useState(true)

  // Filtros
  const [tipo,      setTipo]      = useState('todos')
  const [anioMin,   setAnioMin]   = useState('')
  const [precioMax, setPrecioMax] = useState('')
  const [copied,    setCopied]    = useState(false)

  useEffect(() => { fetchTc().then(setTc) }, [])

  useEffect(() => {
    setLoading(true)
    getVehiculosPublicos({ tipo, anioMin, precioMax }).then(async (data) => {
      setVehiculos(data)
      const ids = data.map(v => v.id)
      const fotos = await getPortadas(ids)
      setPortadas(fotos)
      setLoading(false)
    })
  }, [tipo, anioMin, precioMax])

  function copiarLink() {
    navigator.clipboard.writeText(window.location.origin + '/p/catalogo')
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div style={{ minHeight: '100vh', background: 'var(--c-bg)', padding: 0 }}>

      {/* Header */}
      <header style={{
        background: 'var(--c-card)',
        borderBottom: '1px solid var(--c-border)',
        padding: '12px 24px',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        position: 'sticky', top: 0, zIndex: 100,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div className="brand-mark" style={{ width: 36, height: 36, fontSize: 14, borderRadius: 8 }}>GH</div>
          <div>
            <div style={{ fontWeight: 700, fontSize: 15 }}>GH Cars</div>
            <div style={{ fontSize: 11, color: 'var(--c-fg-3)' }}>Stock disponible</div>
          </div>
        </div>
        <a
          href={`https://wa.me/${WA_NUMBER}`}
          target="_blank"
          rel="noreferrer"
          className="btn btn-primary"
          style={{ fontSize: 13, textDecoration: 'none' }}
        >
          💬 Contactar
        </a>
      </header>

      {/* Filtros */}
      <div style={{
        background: 'var(--c-card)',
        borderBottom: '1px solid var(--c-border)',
        padding: '12px 24px',
        display: 'flex', flexWrap: 'wrap', gap: 10, alignItems: 'center',
      }}>
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {TIPOS.map(t => (
            <button
              key={t}
              className={`btn ${tipo === t ? 'btn-primary' : 'btn-ghost'}`}
              style={{ fontSize: 12, padding: '4px 12px' }}
              onClick={() => setTipo(t)}
            >
              {TIPOS_LABEL[t]}
            </button>
          ))}
        </div>
        <div style={{ display: 'flex', gap: 8, marginLeft: 'auto', flexWrap: 'wrap' }}>
          <input
            className="input"
            type="number"
            placeholder="Año desde"
            value={anioMin}
            onChange={e => setAnioMin(e.target.value)}
            style={{ width: 110, fontSize: 13 }}
          />
          <input
            className="input"
            type="number"
            placeholder="Precio max USD"
            value={precioMax}
            onChange={e => setPrecioMax(e.target.value)}
            style={{ width: 140, fontSize: 13 }}
          />
          {(anioMin || precioMax) && (
            <button className="btn btn-ghost" style={{ fontSize: 12 }} onClick={() => { setAnioMin(''); setPrecioMax('') }}>
              Limpiar
            </button>
          )}
        </div>
      </div>

      {/* Grilla */}
      <div style={{ padding: '24px', maxWidth: 1200, margin: '0 auto' }}>
        {loading ? (
          <div style={{ textAlign: 'center', color: 'var(--c-fg-3)', padding: 60, fontSize: 15 }}>
            Cargando vehículos…
          </div>
        ) : vehiculos.length === 0 ? (
          <div style={{ textAlign: 'center', color: 'var(--c-fg-3)', padding: 60 }}>
            <div style={{ fontSize: 40, marginBottom: 12 }}>🚗</div>
            <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 4 }}>No hay vehículos disponibles</div>
            <div style={{ fontSize: 13 }}>Consultanos por WhatsApp para próximos ingresos.</div>
          </div>
        ) : (
          <>
            <div style={{ fontSize: 13, color: 'var(--c-fg-3)', marginBottom: 16 }}>
              {vehiculos.length} vehículo{vehiculos.length !== 1 ? 's' : ''} disponible{vehiculos.length !== 1 ? 's' : ''}
              {tc && tc !== FALLBACK_TC && <span> · TC USD/ARS: {tc.toLocaleString('es-AR')}</span>}
            </div>
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))',
              gap: 20,
            }}>
              {vehiculos.map(v => (
                <CardPublica key={v.id} v={v} foto={portadas[v.id]} tc={tc} />
              ))}
            </div>
          </>
        )}
      </div>

      {/* Footer */}
      <footer style={{
        borderTop: '1px solid var(--c-border)',
        padding: '20px 24px',
        textAlign: 'center',
        color: 'var(--c-fg-3)',
        fontSize: 12,
        marginTop: 40,
      }}>
        <div style={{ fontWeight: 600, marginBottom: 4 }}>GH Cars</div>
        <div>Los precios están expresados en USD. Precio en ARS calculado al dólar blue.</div>
        <div style={{ marginTop: 8, display: 'flex', justifyContent: 'center', gap: 8, alignItems: 'center' }}>
          <code style={{ padding: '4px 10px', background: 'var(--c-card-2)', borderRadius: 4, fontSize: 11 }}>
            {typeof window !== 'undefined' ? window.location.origin + '/p/catalogo' : '/p/catalogo'}
          </code>
          <button className="btn btn-ghost" style={{ fontSize: 11, padding: '4px 10px' }} onClick={copiarLink}>
            {copied ? '✓ Copiado' : 'Copiar link'}
          </button>
        </div>
      </footer>

    </div>
  )
}
