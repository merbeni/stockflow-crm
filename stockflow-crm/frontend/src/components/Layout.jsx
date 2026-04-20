import { useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const NAV = [
  { to: '/products',        label: 'Products' },
  { to: '/suppliers',       label: 'Suppliers' },
  { to: '/invoices',        label: 'Invoices' },
  { to: '/stock-movements', label: 'Stock Movements' },
  { to: '/customers',       label: 'Customers' },
  { to: '/orders',          label: 'Orders' },
]

function SidebarContent({ user, onLogout, onClose }) {
  return (
    <>
      <div className="px-5 py-5 border-b border-brand-border flex items-center justify-between">
        <span className="text-lg font-bold text-primary-text">StockFlow</span>
        <button
          onClick={onClose}
          className="md:hidden text-tx-muted hover:text-tx-secondary text-2xl leading-none p-1"
          aria-label="Close menu"
        >
          &times;
        </button>
      </div>
      <nav className="flex-1 py-4 space-y-0.5 px-2">
        {NAV.map(({ to, label }) => (
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
      <div className="px-4 py-4 border-t border-brand-border">
        <p className="text-xs text-tx-muted truncate mb-2">{user?.email ?? ''}</p>
        <button
          onClick={onLogout}
          className="w-full text-left text-xs text-red-500 hover:text-red-700 font-medium"
        >
          Sign out
        </button>
      </div>
    </>
  )
}

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)

  function handleLogout() {
    logout()
    navigate('/login')
  }

  return (
    <div className="flex h-screen bg-page">
      {/* Desktop sidebar */}
      <aside className="hidden md:flex w-56 bg-sidebar border-r border-brand-border flex-col shrink-0">
        <SidebarContent user={user} onLogout={handleLogout} onClose={() => {}} />
      </aside>

      {/* Mobile drawer overlay */}
      {open && (
        <div className="fixed inset-0 z-40 md:hidden">
          <div className="absolute inset-0 bg-black/40" onClick={() => setOpen(false)} />
          <aside className="absolute left-0 top-0 h-full w-64 bg-sidebar border-r border-brand-border flex flex-col z-50">
            <SidebarContent user={user} onLogout={handleLogout} onClose={() => setOpen(false)} />
          </aside>
        </div>
      )}

      {/* Main area */}
      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        {/* Mobile top bar */}
        <header className="md:hidden flex items-center justify-between px-4 py-3 bg-sidebar border-b border-brand-border shrink-0">
          <span className="text-base font-bold text-primary-text">StockFlow</span>
          <button
            onClick={() => setOpen(true)}
            className="text-tx-secondary p-1 rounded-md hover:bg-brand-border"
            aria-label="Open menu"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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
