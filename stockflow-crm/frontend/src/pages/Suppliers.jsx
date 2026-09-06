import { useEffect, useState } from 'react'
import client from '../api/client'
import { getErrorMessage, getFieldErrors } from '../api/errors'
import ErrorBanner from '../components/ui/ErrorBanner'
import FormField from '../components/ui/FormField'
import Modal from '../components/ui/Modal'
import {
  email as validarEmail,
  nombrePersona,
  requerido,
  telefono,
  validarFormulario,
} from '../utils/validation'

const VACIO = { name: '', contact_name: '', email: '', phone: '' }

const REGLAS = {
  // El nombre del proveedor es el de una empresa: puede llevar números.
  name: requerido,
  contact_name: nombrePersona,
  email: validarEmail,
  phone: (valor) => (valor?.trim() ? telefono(valor) : null),
}

const CAMPOS = [
  { key: 'name', label: 'Razón social', required: true },
  { key: 'contact_name', label: 'Nombre de contacto', required: true },
  { key: 'email', label: 'Correo electrónico', type: 'email', required: true },
  { key: 'phone', label: 'Teléfono', hint: 'Opcional.' },
]

export default function Suppliers() {
  const [suppliers, setSuppliers] = useState([])
  const [modal, setModal] = useState(null)
  const [form, setForm] = useState(VACIO)
  const [errores, setErrores] = useState({})
  const [error, setError] = useState('')
  const [errorGeneral, setErrorGeneral] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  async function load() {
    setLoading(true)
    try {
      const { data } = await client.get('/suppliers')
      setSuppliers(data)
      setErrorGeneral('')
    } catch (err) {
      setErrorGeneral(getErrorMessage(err, 'No pudimos cargar los proveedores.'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  function openCreate() {
    setForm(VACIO)
    setErrores({})
    setError('')
    setModal('create')
  }

  function openEdit(s) {
    setForm({
      name: s.name,
      contact_name: s.contact_name ?? '',
      email: s.email ?? '',
      phone: s.phone ?? '',
    })
    setErrores({})
    setError('')
    setModal(s)
  }

  function actualizar(campo, valor) {
    setForm((f) => ({ ...f, [campo]: valor }))
    if (errores[campo]) setErrores((e) => ({ ...e, [campo]: REGLAS[campo](valor) }))
  }

  async function handleSave(e) {
    e.preventDefault()
    setError('')

    const encontrados = validarFormulario(form, REGLAS)
    setErrores(encontrados)
    if (Object.keys(encontrados).length > 0) {
      setError('Revisá los campos marcados antes de guardar.')
      return
    }

    setSaving(true)
    const body = { ...form, phone: form.phone.trim() || null }
    try {
      if (modal === 'create') {
        await client.post('/suppliers', body)
      } else {
        await client.put(`/suppliers/${modal.id}`, body)
      }
      setModal(null)
      load()
    } catch (err) {
      setError(getErrorMessage(err, 'No pudimos guardar el proveedor.'))
      setErrores((previos) => ({ ...previos, ...getFieldErrors(err) }))
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(s) {
    if (!confirm(`¿Eliminar el proveedor «${s.name}»?`)) return
    try {
      await client.delete(`/suppliers/${s.id}`)
      setErrorGeneral('')
      load()
    } catch (err) {
      setErrorGeneral(getErrorMessage(err, 'No pudimos eliminar el proveedor.'))
    }
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-bold text-tx-primary">Proveedores</h1>
        <button
          onClick={openCreate}
          className="rounded-lg bg-secondary px-4 py-2 text-sm font-medium text-secondary-text transition hover:bg-secondary-dark"
        >
          + Nuevo proveedor
        </button>
      </div>

      <ErrorBanner
        message={errorGeneral}
        className="mb-4"
        onDismiss={() => setErrorGeneral('')}
      />

      {loading ? (
        <p className="text-sm text-tx-muted">Cargando…</p>
      ) : (
        <div className="overflow-hidden rounded-xl border border-brand-border bg-surface shadow">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[480px] text-sm">
              <thead className="border-b border-brand-border bg-sidebar text-xs uppercase tracking-wide text-tx-muted">
                <tr>
                  {['Razón social', 'Contacto', 'Correo', 'Teléfono', ''].map((h) => (
                    <th key={h} className="px-4 py-3 text-left font-medium">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {suppliers.map((s) => (
                  <tr key={s.id}>
                    <td className="px-4 py-3 font-medium text-tx-primary">{s.name}</td>
                    <td className="px-4 py-3 text-tx-secondary">{s.contact_name ?? '—'}</td>
                    <td className="px-4 py-3 text-tx-secondary">{s.email ?? '—'}</td>
                    <td className="px-4 py-3 text-tx-secondary">{s.phone ?? '—'}</td>
                    <td className="space-x-3 px-4 py-3 text-right">
                      <button
                        onClick={() => openEdit(s)}
                        className="text-xs text-primary-text hover:underline"
                      >
                        Editar
                      </button>
                      <button
                        onClick={() => handleDelete(s)}
                        className="text-xs text-danger hover:underline"
                      >
                        Eliminar
                      </button>
                    </td>
                  </tr>
                ))}
                {suppliers.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-4 py-6 text-center text-tx-muted">
                      Todavía no hay proveedores.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {modal && (
        <Modal
          title={modal === 'create' ? 'Nuevo proveedor' : 'Editar proveedor'}
          onClose={() => setModal(null)}
          disabled={saving}
        >
          <form onSubmit={handleSave} noValidate className="space-y-3">
            <ErrorBanner message={error} />
            {CAMPOS.map(({ key, label, type, required, hint }) => (
              <FormField
                key={key}
                name={key}
                label={label}
                type={type}
                required={required}
                hint={hint}
                disabled={saving}
                value={form[key]}
                error={errores[key]}
                onChange={(e) => actualizar(key, e.target.value)}
                onBlur={() => setErrores((x) => ({ ...x, [key]: REGLAS[key](form[key]) }))}
              />
            ))}
            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setModal(null)}
                disabled={saving}
                className="rounded-lg border border-input-border px-4 py-1.5 text-sm hover:bg-sidebar disabled:opacity-50"
              >
                Cancelar
              </button>
              <button
                type="submit"
                disabled={saving}
                className="min-w-[90px] rounded-lg bg-secondary px-4 py-1.5 text-sm text-secondary-text hover:bg-secondary-dark disabled:cursor-not-allowed disabled:opacity-50"
              >
                {saving ? 'Guardando…' : 'Guardar'}
              </button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  )
}
