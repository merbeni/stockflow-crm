import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

/**
 * Restringe una ruta al rol de administrador.
 *
 * Es solo una comodidad de la interfaz: la autorización real la hace el
 * backend con la dependencia `require_admin`.
 */
export default function AdminRoute({ children }) {
  const { user, loading, isAdmin } = useAuth()

  if (loading) return <p className="text-sm text-tx-muted">Cargando…</p>
  if (!user) return <Navigate to="/login" replace />

  if (!isAdmin) {
    return (
      <div className="rounded-xl border border-brand-border bg-surface p-8 text-center shadow">
        <h1 className="mb-2 text-lg font-bold text-tx-primary">Acceso restringido</h1>
        <p className="text-sm text-tx-muted">
          Esta sección es solo para administradores de la organización.
        </p>
      </div>
    )
  }

  return children
}
