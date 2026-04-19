import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import Layout from './components/Layout'
import PrivateRoute from './components/PrivateRoute'
import Login from './pages/Login'
import Products from './pages/Products'
import Suppliers from './pages/Suppliers'
import Invoices from './pages/Invoices'
import StockMovements from './pages/StockMovements'
import Customers from './pages/Customers'
import Orders from './pages/Orders'

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
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
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
