import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import client, { PARAM_EXPIRADA, PARAM_VOLVER } from '../api/client'
import { getErrorMessage, getFieldErrors } from '../api/errors'
import ErrorBanner from '../components/ui/ErrorBanner'
import FormField from '../components/ui/FormField'
import { useAuth } from '../context/AuthContext'
import {
  email as validarEmail,
  requerido,
  validarFormulario,
} from '../utils/validation'

// La contraseña acá solo tiene que estar: las reglas de fortaleza son del alta.
// Exigirlas al ingresar delataría el formato de las contraseñas guardadas y
// dejaría afuera a quien tenga una anterior a la regla actual.
const REGLAS = {
  email: validarEmail,
  password: requerido,
}

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [errores, setErrores] = useState({})
  const [error, setError] = useState('')
  const [aviso, setAviso] = useState('')
  const [necesitaVerificar, setNecesitaVerificar] = useState(false)
  const [loading, setLoading] = useState(false)
  const [reenviando, setReenviando] = useState(false)
  const [parametros] = useSearchParams()
  const [sesionExpirada, setSesionExpirada] = useState(
    () => parametros.get(PARAM_EXPIRADA) === '1'
  )

  // A dónde volver una vez que la persona vuelve a entrar. Solo se aceptan
  // rutas propias: una URL completa acá sería un redirect abierto, un clásico
  // para llevar a alguien a un sitio de phishing con un enlace que parece del
  // sistema.
  // Se calcula una sola vez: más abajo se limpia la barra de direcciones y el
  // destino no debe depender de que ese borrado llegue o no al router.
  const [volverA] = useState(() => {
    const destino = parametros.get(PARAM_VOLVER)
    if (!destino || !destino.startsWith('/') || destino.startsWith('//')) return '/'
    return destino
  })

  // La marca ya se leyó: se saca de la barra de direcciones para que el aviso
  // no reaparezca si la persona recarga o guarda el enlace.
  useEffect(() => {
    if (window.location.search) window.history.replaceState({}, '', '/login')
  }, [])

  function actualizar(campo, valor) {
    if (campo === 'email') setEmail(valor)
    else setPassword(valor)
    // Solo se revalida lo que ya estaba marcado: avisar mientras se escribe por
    // primera vez es molestar antes de tiempo.
    if (errores[campo]) {
      setErrores((e) => ({ ...e, [campo]: REGLAS[campo](valor) }))
    }
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setAviso('')
    setSesionExpirada(false)
    setNecesitaVerificar(false)

    // Antes no había ninguna comprobación acá: el formulario vacío viajaba al
    // servidor y volvía con un mensaje que solo hablaba del correo, aunque la
    // contraseña también faltara, y sin marcar ningún campo.
    const encontrados = validarFormulario({ email, password }, REGLAS)
    setErrores(encontrados)
    if (Object.keys(encontrados).length > 0) return

    setLoading(true)
    try {
      await login(email, password)
      navigate(volverA, { replace: true })
    } catch (err) {
      setError(getErrorMessage(err, 'No pudimos iniciar sesión.'))
      setErrores((previos) => ({ ...previos, ...getFieldErrors(err) }))
      // El backend responde 403 cuando la cuenta existe pero falta verificar
      // el correo: en ese caso ofrecemos reenviar el enlace.
      if (err.response?.status === 403) setNecesitaVerificar(true)
    } finally {
      setLoading(false)
    }
  }

  async function reenviarVerificacion() {
    setError('')
    setReenviando(true)
    try {
      const { data } = await client.post('/auth/resend-verification', { email })
      setAviso(data.message)
      setNecesitaVerificar(false)
    } catch (err) {
      setError(getErrorMessage(err, 'No pudimos reenviar el correo.'))
    } finally {
      setReenviando(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-page p-4">
      <div className="w-full max-w-sm rounded-2xl border border-brand-border bg-surface p-8 shadow">
        <h1 className="mb-1 text-2xl font-bold text-tx-primary">StockFlow CRM</h1>
        <p className="mb-6 text-sm text-tx-muted">Ingresá a tu cuenta</p>

        {sesionExpirada && (
          <p className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
            Tu sesión se cerró por inactividad. Ingresá de nuevo para seguir
            donde estabas.
          </p>
        )}

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
            disabled={reenviando}
            className="mb-4 w-full rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-800 hover:bg-amber-100 disabled:opacity-60"
          >
            {reenviando ? 'Enviando…' : 'Reenviarme el correo de verificación'}
          </button>
        )}

        <form onSubmit={handleSubmit} noValidate className="space-y-4">
          <FormField
            name="email"
            label="Correo electrónico"
            type="email"
            required
            value={email}
            error={errores.email}
            onChange={(e) => actualizar('email', e.target.value)}
            onBlur={() => setErrores((x) => ({ ...x, email: REGLAS.email(email) }))}
            disabled={loading}
          />
          <FormField
            name="password"
            label="Contraseña"
            type="password"
            required
            value={password}
            error={errores.password}
            onChange={(e) => actualizar('password', e.target.value)}
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
