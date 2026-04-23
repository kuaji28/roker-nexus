import { createContext, useContext } from 'react'

export const UserContext = createContext(null)

export function useUser() {
  return useContext(UserContext)
}

// Helpers de permisos basados en rol
export function canSeeCosto(rol)      { return rol === 'dueno' }
export function canSeePrecioBase(rol) { return rol === 'dueno' || rol === 'vendedor' }
export function canSeeMargen(rol)     { return rol === 'dueno' }
export function canEditVehiculo(rol)  { return rol === 'dueno' || rol === 'vendedor' }
export function canVerIngresos(rol)   { return rol === 'dueno' }
export function canCambiarEstado(rol) { return rol === 'dueno' || rol === 'vendedor' }
