import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import client from '../api/client'
import { getErrorMessage } from '../api/errors'

export default function VerifyEmail() {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token')
  const [estado, setEstado] = useState('verificando') // verificando | ok | error
  const [mensaje, setMensaje] = useState('')
  // En modo estricto de React el efecto corre dos veces; el token es de un solo
  // uso, así que la segunda llamada fallaría y mostraría un error falso.
  const yaEjecutado = useRef(false)

  useEffect(() => {
    if (yaEjecutado.current) return
    yaEjecutado.current = true

    if (!token) {
      setEstado('error')
      setMensaje('El enlace está incompleto: falta el código de verificación.')
      return
    }

    client
      .get('/auth/verify-email', { params: { token } })
      .then(({ data }) => {
        setEstado('ok')
        setMensaje(data.message)
      })
      .catch((err) => {
        setEstado('error')
        setMensaje(getErrorMessage(err, 'No pudimos verificar tu correo.'))
      })
  }, [token])

  return (
    <div className="flex min-h-screen items-center justify-center bg-page p-4">
      <div className="w-full max-w-md rounded-2xl border border-brand-border bg-surface p-8 text-center shadow">
        {estado === 'verificando' && (
          <>
            <h1 className="mb-2 text-lg font-bold text-tx-primary">
              Verificando tu correo…
            </h1>
            <p className="text-sm text-tx-muted">Esto toma solo un momento.</p>
          </>
        )}

        {estado === 'ok' && (
          <>
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-green-100">
              <svg className="h-6 w-6 text-green-700" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h1 className="mb-2 text-lg font-bold text-tx-primary">Correo verificado</h1>
            <p className="mb-6 text-sm text-tx-secondary">{mensaje}</p>
            <Link
              to="/login"
              className="inline-block rounded-lg bg-secondary px-5 py-2 text-sm font-medium text-secondary-text transition hover:bg-secondary-dark"
            >
              Iniciar sesión
            </Link>
          </>
        )}

        {estado === 'error' && (
          <>
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-red-100">
              <svg className="h-6 w-6 text-danger" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </div>
            <h1 className="mb-2 text-lg font-bold text-tx-primary">
              No pudimos verificar tu correo
            </h1>
            <p className="mb-6 text-sm text-tx-secondary">{mensaje}</p>
            <Link
              to="/login"
              className="inline-block rounded-lg border border-input-border px-5 py-2 text-sm hover:bg-sidebar"
            >
              Volver al inicio de sesión
            </Link>
          </>
        )}
      </div>
    </div>
  )
}
