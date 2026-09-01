import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import client from '../api/client'
import { getErrorMessage, getFieldErrors } from '../api/errors'
import ErrorBanner from '../components/ui/ErrorBanner'
import FormField from '../components/ui/FormField'
import {
  email as validarEmail,
  nombrePersona,
  password as validarPassword,
  requerido,
  telefono,
  validarFormulario,
} from '../utils/validation'

const VACIO = {
  organization_name: '',
  full_name: '',
  email: '',
  phone: '',
  password: '',
}

const REGLAS = {
  organization_name: requerido,
  full_name: nombrePersona,
  email: validarEmail,
  phone: telefono,
  password: validarPassword,
}

const CAMPOS = [
  {
    key: 'organization_name',
    label: 'Nombre de tu empresa u organización',
    placeholder: 'Distribuidora del Sur',
    hint: 'Así vas a identificar tu CRM. Podés cambiarlo después.',
  },
  { key: 'full_name', label: 'Tu nombre y apellido', placeholder: 'Ana Gómez' },
  { key: 'email', label: 'Correo electrónico', type: 'email', placeholder: 'ana@empresa.com' },
  { key: 'phone', label: 'Teléfono de contacto', placeholder: '+54 11 5555-1234' },
  {
    key: 'password',
    label: 'Contraseña',
    type: 'password',
    hint: 'Mínimo 8 caracteres, con al menos una letra y un número.',
  },
]

export default function Signup() {
  const navigate = useNavigate()
  const [form, setForm] = useState(VACIO)
  const [errores, setErrores] = useState({})
  const [tocados, setTocados] = useState({})
  const [error, setError] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [exito, setExito] = useState(null)

  function actualizar(campo, valor) {
    setForm((f) => ({ ...f, [campo]: valor }))
    if (tocados[campo]) {
      setErrores((e) => ({ ...e, [campo]: REGLAS[campo](valor) }))
    }
  }

  function marcarTocado(campo) {
    setTocados((t) => ({ ...t, [campo]: true }))
    setErrores((e) => ({ ...e, [campo]: REGLAS[campo](form[campo]) }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')

    const encontrados = validarFormulario(form, REGLAS)
    setTocados(Object.fromEntries(CAMPOS.map(({ key }) => [key, true])))
    setErrores(encontrados)
    if (Object.keys(encontrados).length > 0) {
      setError('Revisá los campos marcados antes de continuar.')
      return
    }

    setEnviando(true)
    try {
      const { data } = await client.post('/auth/signup', form)
      setExito(data)
    } catch (err) {
      setError(getErrorMessage(err, 'No pudimos crear tu cuenta.'))
      setErrores((previos) => ({ ...previos, ...getFieldErrors(err) }))
    } finally {
      setEnviando(false)
    }
  }

  if (exito) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-page p-4">
        <div className="w-full max-w-md rounded-2xl border border-brand-border bg-surface p-8 text-center shadow">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-green-100">
            <svg className="h-6 w-6 text-green-700" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h1 className="mb-2 text-lg font-bold text-tx-primary">
            ¡Tu CRM «{exito.organization?.name}» está creado!
          </h1>
          <p className="mb-6 text-sm text-tx-secondary">{exito.message}</p>
          <p className="mb-6 rounded-lg bg-sidebar px-3 py-2 text-xs text-tx-muted">
            Cuenta: <strong className="text-tx-secondary">{exito.user?.email}</strong>
            <br />
            Rol: administrador de la organización
          </p>
          <button
            onClick={() => navigate('/login')}
            className="w-full rounded-lg bg-secondary py-2 text-sm font-medium text-secondary-text transition hover:bg-secondary-dark"
          >
            Ir a iniciar sesión
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-page p-4">
      <div className="w-full max-w-md rounded-2xl border border-brand-border bg-surface p-8 shadow">
        <h1 className="mb-1 text-2xl font-bold text-tx-primary">Creá tu CRM</h1>
        <p className="mb-6 text-sm text-tx-muted">
          Registrate y vas a ser el administrador de tu propia organización, con
          sus productos, clientes y facturas separados del resto.
        </p>

        <ErrorBanner message={error} className="mb-4" onDismiss={() => setError('')} />

        <form onSubmit={handleSubmit} noValidate className="space-y-3">
          {CAMPOS.map(({ key, label, type, placeholder, hint }) => (
            <FormField
              key={key}
              name={key}
              label={label}
              type={type}
              required
              placeholder={placeholder}
              hint={hint}
              value={form[key]}
              error={errores[key]}
              disabled={enviando}
              onChange={(e) => actualizar(key, e.target.value)}
              onBlur={() => marcarTocado(key)}
            />
          ))}

          <button
            type="submit"
            disabled={enviando}
            className="w-full rounded-lg bg-secondary py-2 text-sm font-medium text-secondary-text transition hover:bg-secondary-dark disabled:opacity-50"
          >
            {enviando ? 'Creando tu CRM…' : 'Crear mi CRM'}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-tx-muted">
          ¿Ya tenés una cuenta?{' '}
          <Link to="/login" className="font-medium text-primary-text hover:underline">
            Iniciá sesión
          </Link>
        </p>
      </div>
    </div>
  )
}
