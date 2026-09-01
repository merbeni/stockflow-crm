import { useEffect, useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import client from '../api/client'
import { useAuth } from '../context/AuthContext'

const NAV = [
  { to: '/products',        label: 'Productos' },
  { to: '/suppliers',       label: 'Proveedores' },
  { to: '/invoices',        label: 'Facturas' },
  { to: '/stock-movements', label: 'Movimientos de stock' },
  { to: '/customers',       label: 'Clientes' },
  { to: '/orders',          label: 'Pedidos' },
]

const NAV_ADMIN = [{ to: '/users', label: 'Usuarios' }]

function SidebarContent({ user, organizacion, isAdmin, onLogout, onClose }) {
  const enlaces = isAdmin ? [...NAV, ...NAV_ADMIN] : NAV

  return (
    <>
      <div className="flex items-center justify-between border-b border-brand-border px-5 py-5">
        <div className="min-w-0">
          <span className="block text-lg font-bold text-primary-text">StockFlow</span>
          {organizacion && (
            <span className="block truncate text-xs text-tx-muted">{organizacion.name}</span>
          )}
        </div>
        <button
          onClick={onClose}
          className="p-1 text-2xl leading-none text-tx-muted hover:text-tx-secondary md:hidden"
          aria-label="Cerrar menú"
        >
          &times;
        </button>
      </div>
      <nav className="flex-1 space-y-0.5 px-2 py-4">
        {enlaces.map(({ to, label }) => (
          <NavLink
            key={to}
            to={to}
            onClick={onClose}
            className={({ isActive }) =>
              `block rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-primary text-primary-text'
                  : 'text-tx-secondary hover:bg-brand-border hover:text-primary-text'
              }`
            }
          >
            {label}
          </NavLink>
        ))}
      </nav>
      <div className="border-t border-brand-border px-4 py-4">
        <p className="truncate text-xs font-medium text-tx-secondary">
          {user?.full_name ?? user?.email ?? ''}
        </p>
        {user?.full_name && (
          <p className="mb-1 truncate text-xs text-tx-muted">{user.email}</p>
        )}
        <p className="mb-2 text-xs text-tx-muted">
          {isAdmin ? 'Administrador' : 'Operador'}
        </p>
        <button
          onClick={onLogout}
          className="w-full text-left text-xs font-medium text-red-500 hover:text-red-700"
        >
          Cerrar sesión
        </button>
      </div>
    </>
  )
}

export default function Layout() {
  const { user, isAdmin, logout } = useAuth()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [organizacion, setOrganizacion] = useState(null)

  useEffect(() => {
    if (!user) return
    let cancelado = false
    client
      .get('/auth/my-organization')
      .then(({ data }) => {
        if (!cancelado) setOrganizacion(data)
      })
      .catch(() => {
        // El nombre de la organización es informativo: si falla, no se muestra.
      })
    return () => {
      cancelado = true
    }
  }, [user])

  function handleLogout() {
    logout()
    navigate('/login')
  }

  const sidebarProps = { user, organizacion, isAdmin, onLogout: handleLogout }

  return (
    <div className="flex h-screen bg-page">
      {/* Barra lateral de escritorio */}
      <aside className="hidden w-56 shrink-0 flex-col border-r border-brand-border bg-sidebar md:flex">
        <SidebarContent {...sidebarProps} onClose={() => {}} />
      </aside>

      {/* Cajón lateral en móvil */}
      {open && (
        <div className="fixed inset-0 z-40 md:hidden">
          <div className="absolute inset-0 bg-black/40" onClick={() => setOpen(false)} />
          <aside className="absolute left-0 top-0 z-50 flex h-full w-64 flex-col border-r border-brand-border bg-sidebar">
            <SidebarContent {...sidebarProps} onClose={() => setOpen(false)} />
          </aside>
        </div>
      )}

      {/* Área principal */}
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        {/* Barra superior en móvil */}
        <header className="flex shrink-0 items-center justify-between border-b border-brand-border bg-sidebar px-4 py-3 md:hidden">
          <span className="text-base font-bold text-primary-text">StockFlow</span>
          <button
            onClick={() => setOpen(true)}
            className="rounded-md p-1 text-tx-secondary hover:bg-brand-border"
            aria-label="Abrir menú"
          >
            <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
        </header>

        <main className="flex-1 overflow-y-auto overflow-x-hidden p-4 md:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
