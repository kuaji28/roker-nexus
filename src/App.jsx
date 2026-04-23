import { useState } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import Login from './screens/Login'
import Dashboard from './screens/Dashboard'
import Catalogo from './screens/Catalogo'
import Detalle from './screens/Detalle'
import Placeholder from './screens/Placeholder'
import IngresoScreen from './screens/Ingreso'

function AppShell({ onLogout }) {
  const tc = 1415
  return (
    <div className="app">
      <Sidebar tc={tc} />
      <div style={{ minWidth: 0, flex: 1 }}>
        <Routes>
          <Route path="/"           element={<Dashboard onLogout={onLogout} />} />
          <Route path="/catalogo"   element={<Catalogo  onLogout={onLogout} />} />
          <Route path="/vehiculo/:id" element={<Detalle onLogout={onLogout} />} />
          <Route path="/ingreso"    element={<IngresoScreen onLogout={onLogout} />} />
          <Route path="/ventas"     element={<Placeholder title="Ventas"            onLogout={onLogout} />} />
          <Route path="/doc"        element={<Placeholder title="Documentación"     onLogout={onLogout} />} />
          <Route path="/reportes"   element={<Placeholder title="Reportes"          onLogout={onLogout} />} />
          <Route path="/gerente"    element={<Placeholder title="Dashboard Gerente" onLogout={onLogout} />} />
          <Route path="/vendedores" element={<Placeholder title="Vendedores"        onLogout={onLogout} />} />
          <Route path="/cobranza"   element={<Placeholder title="Cobranza"          onLogout={onLogout} />} />
          <Route path="/config"     element={<Placeholder title="Configuración"     onLogout={onLogout} />} />
          <Route path="*"           element={<Navigate to="/" replace />} />
        </Routes>
      </div>
    </div>
  )
}

export default function App() {
  const [auth, setAuth] = useState(() => sessionStorage.getItem('gh_auth') === '1')

  function handleLogin() {
    sessionStorage.setItem('gh_auth', '1')
    setAuth(true)
  }
  function handleLogout() {
    sessionStorage.removeItem('gh_auth')
    setAuth(false)
  }

  if (!auth) return <Login onLogin={handleLogin} />

  return (
    <BrowserRouter>
      <AppShell onLogout={handleLogout} />
    </BrowserRouter>
  )
}
