import TopBar from '../components/TopBar'
import Icon from '../components/Icon'

// ─── Catálogo de mejoras disponibles ────────────────────────────────────────
const MEJORAS = [
  {
    categoria: 'Comunicación con clientes',
    items: [
      {
        titulo: 'Bot de WhatsApp automático',
        descripcion: 'El sistema manda mensajes automáticos a prospectos: recordatorios de visita, seguimiento post-consulta, y avisos cuando entra un vehículo que les interesó. Sin trabajo manual del vendedor.',
        valor: 'Alto',
        esfuerzo: 'Medio',
        icon: '💬',
      },
      {
        titulo: 'Seguimiento automático por email',
        descripcion: 'Envío de emails personalizados a clientes que compraron hace 6 o 12 meses ofreciendo un vehículo nuevo o la oportunidad de actualizar el que tienen.',
        valor: 'Alto',
        esfuerzo: 'Bajo',
        icon: '📧',
      },
      {
        titulo: 'Recordatorios de vencimiento (patente, seguro, revisión)',
        descripcion: 'El sistema avisa al cliente antes de que venza la patente, el seguro o la revisión técnica del vehículo que compró. Fideliza y genera nueva consulta.',
        valor: 'Medio',
        esfuerzo: 'Bajo',
        icon: '🔔',
      },
    ],
  },
  {
    categoria: 'Vehículos e inventario',
    items: [
      {
        titulo: 'Publicación automática en MercadoLibre',
        descripcion: 'Al ingresar un vehículo al sistema, se publica automáticamente en MercadoLibre con fotos y descripción. Al venderse, se da de baja sin intervención manual.',
        valor: 'Alto',
        esfuerzo: 'Medio',
        icon: '🛒',
      },
      {
        titulo: 'Página web pública del catálogo',
        descripcion: 'Una web pública de GH Cars donde los clientes pueden ver todos los vehículos disponibles con fotos, precio y un botón de contacto directo. Se actualiza sola cuando entra o sale un auto.',
        valor: 'Alto',
        esfuerzo: 'Medio',
        icon: '🌐',
      },
      {
        titulo: 'Historial completo de propietarios',
        descripcion: 'Registro de todos los dueños anteriores de cada vehículo: cuándo compraron, cuándo vendieron, precio pagado, kilómetros al momento de cada transacción.',
        valor: 'Medio',
        esfuerzo: 'Bajo',
        icon: '📋',
      },
      {
        titulo: 'Tasador automático con IA',
        descripcion: 'El sistema sugiere un precio de compra para un vehículo usado basándose en publicaciones actuales de MercadoLibre, año, kilómetros y estado. Asistente para el momento de la tasación.',
        valor: 'Alto',
        esfuerzo: 'Alto',
        icon: '🤖',
      },
      {
        titulo: 'Carga de documentos del vehículo',
        descripcion: 'Subir al sistema el título, cédula verde/azul, verificación policial y facturas. Todo digitalizado y accesible desde cualquier lugar, sin depender de carpetas físicas.',
        valor: 'Medio',
        esfuerzo: 'Bajo',
        icon: '📁',
      },
      {
        titulo: 'Registro de gastos por vehículo',
        descripcion: 'Llevar cuenta de lo que cuesta preparar cada auto: mecánica, lavado, pintura, repuestos. Al final se calcula el margen real de ganancia de cada venta.',
        valor: 'Alto',
        esfuerzo: 'Bajo',
        icon: '🔧',
      },
    ],
  },
  {
    categoria: 'Ventas y finanzas',
    items: [
      {
        titulo: 'Control de financiamientos y cuotas',
        descripcion: 'Para ventas en cuotas: el sistema registra el plan de pago, manda recordatorios cuando vence una cuota, y alerta cuando hay atrasos.',
        valor: 'Alto',
        esfuerzo: 'Medio',
        icon: '💳',
      },
      {
        titulo: 'Dashboard financiero mensual',
        descripcion: 'Resumen automático de cada mes: ingresos totales, vehículos vendidos, ganancias netas, comparación con el mes anterior. Para revisar el negocio de un vistazo.',
        valor: 'Alto',
        esfuerzo: 'Bajo',
        icon: '📊',
      },
      {
        titulo: 'Comisiones de vendedores',
        descripcion: 'Cálculo automático de la comisión de cada vendedor según las ventas del mes. Evita errores y discusiones.',
        valor: 'Medio',
        esfuerzo: 'Bajo',
        icon: '💰',
      },
      {
        titulo: 'Consignaciones',
        descripcion: 'Módulo para manejar vehículos de terceros que la concesionaria vende a comisión. Control del acuerdo, plazo, precio mínimo y liquidación al dueño.',
        valor: 'Medio',
        esfuerzo: 'Medio',
        icon: '🤝',
      },
    ],
  },
  {
    categoria: 'Marketing y captación',
    items: [
      {
        titulo: 'Integración con Instagram / Facebook',
        descripcion: 'Publicar automáticamente los vehículos nuevos en las redes sociales de la concesionaria con fotos y descripción. Sin trabajo extra.',
        valor: 'Alto',
        esfuerzo: 'Medio',
        icon: '📱',
      },
      {
        titulo: 'Formulario web de contacto',
        descripcion: 'Un formulario en el sitio web donde los interesados dejan sus datos. Llegan directo al sistema como prospectos nuevos, sin tener que cargarlos a mano.',
        valor: 'Alto',
        esfuerzo: 'Bajo',
        icon: '📝',
      },
      {
        titulo: 'Campaña de reactivación de clientes',
        descripcion: 'Identificar automáticamente clientes que compraron hace más de un año y mandarles una oferta personalizada. Los datos ya están en el sistema.',
        valor: 'Alto',
        esfuerzo: 'Bajo',
        icon: '🎯',
      },
    ],
  },
  {
    categoria: 'Operación interna',
    items: [
      {
        titulo: 'App móvil para vendedores',
        descripcion: 'Una versión del sistema optimizada para el celular: ver el catálogo, cargar prospectos, consultar el estado de una venta desde cualquier lugar.',
        valor: 'Medio',
        esfuerzo: 'Alto',
        icon: '📲',
      },
      {
        titulo: 'Alertas y notificaciones internas',
        descripcion: 'El sistema avisa cuando un prospecto lleva más de X días sin contacto, cuando vence una gestión, o cuando entra un vehículo que coincide con lo que busca un cliente.',
        valor: 'Alto',
        esfuerzo: 'Bajo',
        icon: '🔔',
      },
      {
        titulo: 'Agenda de test drives',
        descripcion: 'Control de los turnos para probar vehículos: quién, cuándo, qué auto, y registro de si el test drive derivó en venta.',
        valor: 'Medio',
        esfuerzo: 'Bajo',
        icon: '🗓',
      },
    ],
  },
]

const VALOR_COLOR  = { Alto: '#00C48C', Medio: '#F5A623', Bajo: '#6B7280' }
const ESFUERZO_COLOR = { Alto: '#EF4444', Medio: '#F97316', Bajo: '#4D9DE0' }

function Badge({ label, color }) {
  return (
    <span style={{
      display: 'inline-block', fontSize: 10, fontWeight: 600,
      padding: '2px 8px', borderRadius: 20,
      background: color + '22', color: color, letterSpacing: 0.3,
    }}>
      {label}
    </span>
  )
}

export default function Mejoras({ onLogout }) {
  const total = MEJORAS.reduce((sum, c) => sum + c.items.length, 0)

  return (
    <div>
      <TopBar onLogout={onLogout} />
      <div className="main">

        <div className="page-head">
          <div>
            <h1 className="page-title">Mejoras del sistema</h1>
            <p className="page-caption">{total} funciones disponibles para incorporar</p>
          </div>
        </div>

        {/* Intro */}
        <div className="card" style={{ padding: '16px 20px', marginBottom: 24, background: 'var(--c-accent)10', borderLeft: '4px solid var(--c-accent)' }}>
          <p style={{ margin: 0, fontSize: 13, lineHeight: 1.6, color: 'var(--c-fg-1)' }}>
            Esta lista muestra todo lo que se puede agregar al sistema. Cada función es independiente: se puede incorporar una a la vez según prioridades y presupuesto.
            Si alguna te interesa, avisanos y la incluimos en el siguiente desarrollo.
          </p>
          <div style={{ display: 'flex', gap: 16, marginTop: 12, fontSize: 12, color: 'var(--c-fg-2)' }}>
            <span><span style={{ color: VALOR_COLOR.Alto, fontWeight: 700 }}>●</span> Valor Alto = impacto directo en ventas o ahorro de tiempo significativo</span>
            <span><span style={{ color: ESFUERZO_COLOR.Bajo, fontWeight: 700 }}>●</span> Esfuerzo Bajo = se puede implementar rápido</span>
          </div>
        </div>

        {/* Categorías */}
        {MEJORAS.map(cat => (
          <div key={cat.categoria} style={{ marginBottom: 32 }}>
            <h3 style={{ margin: '0 0 14px', fontSize: 14, fontWeight: 700, color: 'var(--c-fg-1)', borderBottom: '1px solid var(--c-border)', paddingBottom: 8 }}>
              {cat.categoria}
            </h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 12 }}>
              {cat.items.map(item => (
                <div key={item.titulo} className="card" style={{ padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: 8 }}>
                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
                    <span style={{ fontSize: 22, lineHeight: 1 }}>{item.icon}</span>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 4 }}>{item.titulo}</div>
                      <div style={{ fontSize: 12, color: 'var(--c-fg-2)', lineHeight: 1.5 }}>{item.descripcion}</div>
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: 6, marginTop: 4 }}>
                    <span style={{ fontSize: 11, color: 'var(--c-fg-3)' }}>Valor:</span>
                    <Badge label={item.valor} color={VALOR_COLOR[item.valor]} />
                    <span style={{ fontSize: 11, color: 'var(--c-fg-3)', marginLeft: 6 }}>Esfuerzo:</span>
                    <Badge label={item.esfuerzo} color={ESFUERZO_COLOR[item.esfuerzo]} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}

      </div>
    </div>
  )
}
