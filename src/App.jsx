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
          <Route path="/"             element={<Dashboard  onLogout={onLogout} />} />
          <Route path="/catalogo"     element={<Catalogo   onLogout={onLogout} />} />
          <Route path="/vehiculo/:id" element={<Detalle    onLogout={onLogout} />} />
          <Route path="/ingreso"      element={<Ingreso    onLogout={onLogout} />} />
          <Route path="/ventas"       element={<Ventas     onLogout={onLogout} />} />
          <Route path="/doc"          element={<Placeholder title="Documentación" onLogout={onLogout} />} />
          <Route path="/reportes"     element={<Reportes   onLogout={onLogout} />} />
          <Route path="/gerente"      element={<Gerente    onLogout={onLogout} />} />
          <Route path="/vendedores"   element={<Vendedores onLogout={onLogout} />} />
          <Route path="/cobranza"     element={<Cobranza   onLogout={onLogout} />} />
          <Route path="/config"       element={<Config     onLogout={onLogout} />} />
          <Route path="*"             element={<Navigate to="/" replace />} />
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
