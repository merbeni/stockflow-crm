import { useEffect, useState } from 'react'
import client from '../api/client'
import { getErrorMessage, getFieldErrors } from '../api/errors'
import ActionButton from '../components/ui/ActionButton'
import ErrorBanner from '../components/ui/ErrorBanner'
import FormField from '../components/ui/FormField'
import Modal from '../components/ui/Modal'
import { useAuth } from '../context/AuthContext'
import {
  email as validarEmail,
  nombrePersona,
  password as validarPassword,
  telefono,
  validarFormulario,
} from '../utils/validation'

const VACIO = { full_name: '', email: '', phone: '', password: '', role: 'operator' }

const REGLAS = {
  full_name: nombrePersona,
  email: validarEmail,
  // El teléfono es opcional en el alta interna.
  phone: (valor) => (valor?.trim() ? telefono(valor) : null),
  password: validarPassword,
}

const ROLES = { admin: 'Administrador', operator: 'Operador' }

export default function Users() {
  const { user: usuarioActual } = useAuth()
  const [usuarios, setUsuarios] = useState([])
  const [organizacion, setOrganizacion] = useState(null)
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState('')
  const [aviso, setAviso] = useState('')
  const [modalAbierto, setModalAbierto] = useState(false)
  const [form, setForm] = useState(VACIO)
  const [errores, setErrores] = useState({})
  const [guardando, setGuardando] = useState(false)

  async function cargar() {
    setCargando(true)
    try {
      const [listado, org] = await Promise.all([
        client.get('/users'),
        client.get('/auth/my-organization'),
      ])
      setUsuarios(listado.data)
      setOrganizacion(org.data)
    } catch (err) {
      // Si no se pudo recargar, la tabla que quedó en pantalla es vieja: no
      // corresponde seguir mostrando el aviso de que el cambio salió bien.
      // Aparecían los dos carteles juntos, uno verde y uno rojo, diciendo cosas
      // opuestas sobre la misma acción.
      setAviso('')
      setError(getErrorMessage(err, 'No pudimos cargar los usuarios.'))
    } finally {
      setCargando(false)
    }
  }

  useEffect(() => {
    cargar()
  }, [])

  function abrirAlta() {
    setForm(VACIO)
    setErrores({})
    setError('')
    setAviso('')
    setModalAbierto(true)
  }

  function actualizar(campo, valor) {
    setForm((f) => ({ ...f, [campo]: valor }))
    if (REGLAS[campo] && errores[campo]) {
      setErrores((e) => ({ ...e, [campo]: REGLAS[campo](valor) }))
    }
  }

  async function guardar(e) {
    e.preventDefault()
    setError('')

    const encontrados = validarFormulario(form, REGLAS)
    setErrores(encontrados)
    if (Object.keys(encontrados).length > 0) {
      setError('Revisá los campos marcados antes de continuar.')
      return
    }

    setGuardando(true)
    try {
      const { data } = await client.post('/users', {
        ...form,
        phone: form.phone.trim() || null,
      })
      setModalAbierto(false)
      setAviso(
        `Se creó la cuenta de ${data.email}. Le enviamos un correo para que ` +
          'verifique su dirección antes del primer ingreso.'
      )
      cargar()
    } catch (err) {
      // El modal queda abierto para no perder lo que ya se cargó.
      setError(getErrorMessage(err, 'No pudimos crear el usuario.'))
      setErrores((previos) => ({ ...previos, ...getFieldErrors(err) }))
    } finally {
      setGuardando(false)
    }
  }

  async function cambiar(usuario, cambios, mensajeExito) {
    setError('')
    setAviso('')
    try {
      await client.put(`/users/${usuario.id}`, cambios)
      setAviso(mensajeExito)
      cargar()
    } catch (err) {
      setError(getErrorMessage(err, 'No pudimos aplicar el cambio.'))
    }
  }

  async function eliminar(usuario) {
    if (!confirm(`¿Eliminar la cuenta de ${usuario.email}?`)) return
    setError('')
    setAviso('')
    try {
      await client.delete(`/users/${usuario.id}`)
      setAviso(`Se eliminó la cuenta de ${usuario.email}.`)
      cargar()
    } catch (err) {
      setError(getErrorMessage(err, 'No pudimos eliminar el usuario.'))
    }
  }

  // Cuántos administradores activos quedan: si es uno solo, no se le ofrecen
  // las acciones que dejarían a la organización sin ningún administrador.
  const adminsActivos = usuarios.filter((u) => u.role === 'admin' && u.is_active).length

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-tx-primary">Usuarios</h1>
          {organizacion && (
            <p className="mt-0.5 text-sm text-tx-muted">
              Organización: <strong className="text-tx-secondary">{organizacion.name}</strong>
            </p>
          )}
        </div>
        <button
          onClick={abrirAlta}
          className="rounded-lg bg-secondary px-4 py-2 text-sm font-medium text-secondary-text transition hover:bg-secondary-dark"
        >
          + Nuevo usuario
        </button>
      </div>

      <ErrorBanner message={error} className="mb-4" onDismiss={() => setError('')} />

      {aviso && (
        <p className="mb-4 rounded-lg border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-700">
          {aviso}
        </p>
      )}

      {cargando ? (
        <p className="text-sm text-tx-muted">Cargando…</p>
      ) : (
        <div className="overflow-hidden rounded-xl border border-brand-border bg-surface shadow">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-sm">
              <thead className="border-b border-brand-border bg-sidebar text-xs uppercase tracking-wide text-tx-muted">
                <tr>
                  {['Nombre', 'Correo', 'Teléfono', 'Rol', 'Estado', ''].map((h) => (
                    <th key={h} className="px-4 py-3 text-left font-medium">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {usuarios.map((u) => {
                  const esUnoMismo = u.id === usuarioActual?.id
                  const esAdminActivo = u.role === 'admin' && u.is_active
                  // Dos motivos distintos para no ofrecer «Hacer operador» ni
                  // «Desactivar» sobre esta fila. El backend rechaza los dos;
                  // acá se evita que el botón siquiera aparezca.
                  const bloqueo = esAdminActivo && esUnoMismo
                    ? 'No podés quitarte el rol de administrador ni desactivar tu propia ' +
                      'cuenta: perderías el acceso a esta pantalla y no podrías deshacerlo. ' +
                      'Pedile a otro administrador que lo haga.'
                    : esAdminActivo && adminsActivos === 1
                      ? 'La organización tiene que conservar al menos un administrador ' +
                        'activo. Asigná el rol de administrador a otra persona para poder ' +
                        'cambiar o desactivar esta cuenta.'
                      : null
                  return (
                    <tr key={u.id} className={u.is_active ? '' : 'bg-gray-50 opacity-60'}>
                      <td className="px-4 py-3 font-medium text-tx-primary">
                        {u.full_name ?? '—'}
                        {esUnoMismo && (
                          <span className="ml-2 text-xs font-normal text-tx-muted">(vos)</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-tx-secondary">{u.email}</td>
                      <td className="px-4 py-3 text-tx-secondary">{u.phone ?? '—'}</td>
                      <td className="px-4 py-3">
                        <span
                          className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
                            u.role === 'admin'
                              ? 'bg-green-100 text-green-800'
                              : 'bg-gray-100 text-gray-700'
                          }`}
                        >
                          {ROLES[u.role]}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-xs">
                        {!u.is_active ? (
                          <span className="text-tx-muted">Desactivado</span>
                        ) : u.is_email_verified ? (
                          <span className="text-success">Activo</span>
                        ) : (
                          <span className="text-warning">Falta verificar el correo</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex flex-wrap justify-end gap-2">
                          {bloqueo ? (
                            <span
                              className="cursor-help text-xs italic text-tx-muted"
                              title={bloqueo}
                            >
                              {esUnoMismo ? 'Tu propia cuenta' : 'Único administrador'}
                            </span>
                          ) : (
                            <>
                              <ActionButton
                                tono={u.role === 'admin' ? 'desactivar' : 'activar'}
                                onClick={() =>
                                  cambiar(
                                    u,
                                    { role: u.role === 'admin' ? 'operator' : 'admin' },
                                    `${u.email} ahora es ${
                                      u.role === 'admin' ? 'operador' : 'administrador'
                                    }.`
                                  )
                                }
                              >
                                {u.role === 'admin' ? 'Hacer operador' : 'Hacer administrador'}
                              </ActionButton>
                              <ActionButton
                                tono={u.is_active ? 'desactivar' : 'activar'}
                                onClick={() =>
                                  cambiar(
                                    u,
                                    { is_active: !u.is_active },
                                    `${u.email} quedó ${u.is_active ? 'desactivado' : 'activo'}.`
                                  )
                                }
                              >
                                {u.is_active ? 'Desactivar' : 'Activar'}
                              </ActionButton>
                            </>
                          )}
                          {!esUnoMismo && (
                            <ActionButton tono="eliminar" onClick={() => eliminar(u)}>
                              Eliminar
                            </ActionButton>
                          )}
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {modalAbierto && (
        <Modal
          title="Nuevo usuario"
          onClose={() => setModalAbierto(false)}
          disabled={guardando}
        >
          <form onSubmit={guardar} noValidate className="space-y-3">
            <ErrorBanner message={error} />
            <FormField
              name="full_name"
              label="Nombre y apellido"
              required
              value={form.full_name}
              error={errores.full_name}
              disabled={guardando}
              onChange={(e) => actualizar('full_name', e.target.value)}
              onBlur={() => setErrores((x) => ({ ...x, full_name: REGLAS.full_name(form.full_name) }))}
            />
            <FormField
              name="email"
              label="Correo electrónico"
              type="email"
              required
              value={form.email}
              error={errores.email}
              disabled={guardando}
              onChange={(e) => actualizar('email', e.target.value)}
              onBlur={() => setErrores((x) => ({ ...x, email: REGLAS.email(form.email) }))}
            />
            <FormField
              name="phone"
              label="Teléfono"
              value={form.phone}
              error={errores.phone}
              disabled={guardando}
              hint="Opcional."
              onChange={(e) => actualizar('phone', e.target.value)}
              onBlur={() => setErrores((x) => ({ ...x, phone: REGLAS.phone(form.phone) }))}
            />
            <FormField
              name="password"
              label="Contraseña inicial"
              type="password"
              required
              value={form.password}
              error={errores.password}
              disabled={guardando}
              hint="Mínimo 8 caracteres, con al menos una letra y un número."
              onChange={(e) => actualizar('password', e.target.value)}
              onBlur={() => setErrores((x) => ({ ...x, password: REGLAS.password(form.password) }))}
            />
            <FormField name="role" label="Rol" required>
              <select
                id="campo-role"
                value={form.role}
                disabled={guardando}
                onChange={(e) => actualizar('role', e.target.value)}
                className="w-full rounded-lg border border-input-border px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-secondary"
              >
                <option value="operator">Operador</option>
                <option value="admin">Administrador</option>
              </select>
            </FormField>

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setModalAbierto(false)}
                disabled={guardando}
                className="rounded-lg border border-input-border px-4 py-1.5 text-sm hover:bg-sidebar disabled:opacity-50"
              >
                Cancelar
              </button>
              <button
                type="submit"
                disabled={guardando}
                className="min-w-[90px] rounded-lg bg-secondary px-4 py-1.5 text-sm text-secondary-text hover:bg-secondary-dark disabled:opacity-50"
              >
                {guardando ? 'Creando…' : 'Crear'}
              </button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  )
}
