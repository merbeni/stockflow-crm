import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import client from '../api/client'
import { getErrorMessage } from '../api/errors'
import ErrorBanner from '../components/ui/ErrorBanner'
import FormField from '../components/ui/FormField'
import { useAuth } from '../context/AuthContext'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [aviso, setAviso] = useState('')
  const [necesitaVerificar, setNecesitaVerificar] = useState(false)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setAviso('')
    setNecesitaVerificar(false)
    setLoading(true)
    try {
      await login(email, password)
      navigate('/')
    } catch (err) {
      setError(getErrorMessage(err, 'No pudimos iniciar sesión.'))
      // El backend responde 403 cuando la cuenta existe pero falta verificar
      // el correo: en ese caso ofrecemos reenviar el enlace.
      if (err.response?.status === 403) setNecesitaVerificar(true)
    } finally {
      setLoading(false)
    }
  }

  async function reenviarVerificacion() {
    setError('')
    try {
      const { data } = await client.post('/auth/resend-verification', { email })
      setAviso(data.message)
      setNecesitaVerificar(false)
    } catch (err) {
      setError(getErrorMessage(err, 'No pudimos reenviar el correo.'))
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-page p-4">
      <div className="w-full max-w-sm rounded-2xl border border-brand-border bg-surface p-8 shadow">
        <h1 className="mb-1 text-2xl font-bold text-tx-primary">StockFlow CRM</h1>
        <p className="mb-6 text-sm text-tx-muted">Ingresá a tu cuenta</p>

        <ErrorBanner message={error} className="mb-4" onDismiss={() => setError('')} />

        {aviso && (
          <p className="mb-4 rounded-lg border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-700">
            {aviso}
          </p>
        )}

        {necesitaVerificar && (
          <button
            type="button"
            onClick={reenviarVerificacion}
            className="mb-4 w-full rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-800 hover:bg-amber-100"
          >
            Reenviarme el correo de verificación
          </button>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <FormField
            name="email"
            label="Correo electrónico"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            disabled={loading}
          />
          <FormField
            name="password"
            label="Contraseña"
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-secondary py-2 text-sm font-medium text-secondary-text transition hover:bg-secondary-dark disabled:opacity-50"
          >
            {loading ? 'Ingresando…' : 'Ingresar'}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-tx-muted">
          ¿No tenés cuenta?{' '}
          <Link to="/signup" className="font-medium text-primary-text hover:underline">
            Creá tu propio CRM
          </Link>
        </p>
      </div>
    </div>
  )
}
