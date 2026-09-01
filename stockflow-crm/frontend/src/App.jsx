import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import ErrorBoundary from './components/ErrorBoundary'
import Layout from './components/Layout'
import PrivateRoute from './components/PrivateRoute'
import AdminRoute from './components/AdminRoute'
import Login from './pages/Login'
import Signup from './pages/Signup'
import VerifyEmail from './pages/VerifyEmail'
import Products from './pages/Products'
import Suppliers from './pages/Suppliers'
import Invoices from './pages/Invoices'
import StockMovements from './pages/StockMovements'
import Customers from './pages/Customers'
import Orders from './pages/Orders'
import Users from './pages/Users'

export default function App() {
  return (
    // El ErrorBoundary envuelve toda la aplicación: si algo falla al renderizar,
    // el usuario ve una pantalla de recuperación en lugar de una en blanco.
    <ErrorBoundary>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/signup" element={<Signup />} />
            <Route path="/verify-email" element={<VerifyEmail />} />
            <Route
              path="/"
              element={
                <PrivateRoute>
                  <Layout />
                </PrivateRoute>
              }
            >
              <Route index element={<Navigate to="/products" replace />} />
              <Route path="products" element={<Products />} />
              <Route path="suppliers" element={<Suppliers />} />
              <Route path="invoices" element={<Invoices />} />
              <Route path="stock-movements" element={<StockMovements />} />
              <Route path="customers" element={<Customers />} />
              <Route path="orders" element={<Orders />} />
              <Route
                path="users"
                element={
                  <AdminRoute>
                    <Users />
                  </AdminRoute>
                }
              />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ErrorBoundary>
  )
}
