import { NavLink } from 'react-router-dom'
import Icon from './Icon'

const NAV = [
  { to: '/',          icon: 'home',      label: 'Dashboard',           tip: 'Resumen general: vehículos disponibles, ventas recientes y métricas clave' },
  { to: '/catalogo',  icon: 'car',       label: 'Catálogo',            tip: 'Ver todos los vehículos disponibles para la venta' },
  { to: '/buscar',    icon: 'search',    label: 'Buscar para cliente', tip: 'Buscar un vehículo según lo que pide un cliente (marca, precio, año...)' },
  { to: '/ingreso',   icon: 'plus',      label: 'Ingresar vehículo',   tip: 'Registrar un nuevo vehículo que entra al stock de la concesionaria' },
  { to: '/ventas',    icon: 'cash',      label: 'Ventas',              tip: 'Registrar una venta y marcar un vehículo como vendido' },
  { to: '/leads',     icon: 'users',     label: 'Prospectos',          tip: 'Personas interesadas en comprar un vehículo — seguimiento y pipeline de ventas' },
  { to: '/clientes',  icon: 'briefcase', label: 'Clientes',            tip: 'Historial de clientes que ya compraron — para recontactar con nuevas ofertas' },
  { to: '/agenda',    icon: 'cal',       label: 'Agenda',              tip: 'Turnos y visitas agendadas al showroom' },
  { to: '/reportes',  icon: 'chart',     label: 'Reportes',            tip: 'Métricas del mes: ventas, ingresos, rotación de stock y más' },
]
const NAV_ADMIN = [
  { to: '/gerente',   icon: 'home',      label: 'Dashboard Gerente',   tip: 'Vista avanzada para dueños: márgenes, performance de vendedores y KPIs' },
  { to: '/gastos',    icon: 'cash',      label: 'Gastos y Margen',     tip: 'Control de gastos por vehículo y margen de ganancia real' },
  { to: '/rotacion',  icon: 'chart',     label: 'Rotación de Stock',   tip: 'Cuántos días tarda cada vehículo en venderse' },
  { to: '/vendedores',icon: 'users',     label: 'Vendedores',          tip: 'Gestión del equipo de ventas: altas, bajas y rendimiento' },
  { to: '/cobranza',  icon: 'card',      label: 'Cobranza',            tip: 'Seguimiento de cuotas y financiamientos pendientes de cobro' },
  { to: '/config',    icon: 'cog',       label: 'Configuración',       tip: 'Ajustes del sistema: PIN de acceso y preferencias generales' },
  { to: '/mejoras',   icon: 'chart',     label: 'Mejoras del sistema', tip: 'Lista de funciones y mejoras disponibles para incorporar al sistema' },
]

export default function Sidebar({ tc }) {
  return (
    <aside className="side">
      <div className="brand">
        <div className="brand-mark">GH</div>
        <div className="brand-txt">
          GH Cars
          <small>Gestión Automotriz</small>
        </div>
      </div>
      <nav className="nav">
        {NAV.map(n => (
          <NavLink key={n.to} to={n.to} end={n.to === '/'} className={({ isActive }) => isActive ? 'on' : ''} title={n.tip}>
            <Icon name={n.icon} size={18} />
            {n.label}
          </NavLink>
        ))}
        <div className="sep">Admin</div>
        {NAV_ADMIN.map(n => (
          <NavLink key={n.to} to={n.to} className={({ isActive }) => isActive ? 'on' : ''} title={n.tip}>
            <Icon name={n.icon} size={18} />
            {n.label}
          </NavLink>
        ))}
      </nav>
      <div className="side-block">
        <h6>Cotización USD</h6>
        <div className="tc-row">
          <strong>$ {(tc || 0).toLocaleString('es-AR')}</strong>
          <small>ARS</small>
        </div>
      </div>
    </aside>
  )
}
