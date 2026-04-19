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

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/login')
  }

  return (
    <div className="flex h-screen bg-page">
      {/* Sidebar */}
      <aside className="w-56 bg-sidebar border-r border-brand-border flex flex-col">
        <div className="px-5 py-5 border-b border-brand-border">
          <span className="text-lg font-bold text-primary-text">StockFlow</span>
        </div>
        <nav className="flex-1 py-4 space-y-0.5 px-2">
          {NAV.map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
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
            onClick={handleLogout}
            className="w-full text-left text-xs text-red-500 hover:text-red-700 font-medium"
          >
            Sign out
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto p-8">
        <Outlet />
      </main>
    </div>
  )
}
