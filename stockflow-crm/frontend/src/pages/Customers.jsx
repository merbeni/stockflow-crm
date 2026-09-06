import { useEffect, useState } from 'react'
import client from '../api/client'
import { getErrorMessage, getFieldErrors } from '../api/errors'
import Badge from '../components/ui/Badge'
import ErrorBanner from '../components/ui/ErrorBanner'
import FormField from '../components/ui/FormField'
import Modal from '../components/ui/Modal'
import {
  email as validarEmail,
  nombrePersona,
  telefono,
  validarFormulario,
} from '../utils/validation'

const VACIO = { name: '', email: '', phone: '', address: '' }

const REGLAS = {
  name: nombrePersona,
  email: validarEmail,
  phone: telefono,
}

const CAMPOS = [
  { key: 'name', label: 'Nombre y apellido', required: true },
  { key: 'email', label: 'Correo electrónico', type: 'email', required: true },
  { key: 'phone', label: 'Teléfono', required: true },
  { key: 'address', label: 'Dirección', hint: 'Opcional.' },
]

export default function Customers() {
  const [customers, setCustomers] = useState([])
  const [modal, setModal] = useState(null)
  const [form, setForm] = useState(VACIO)
  const [errores, setErrores] = useState({})
  const [error, setError] = useState('')
  const [errorGeneral, setErrorGeneral] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [history, setHistory] = useState(null) // { customer, orders } | { loading }

  async function load() {
    setLoading(true)
    try {
      const { data } = await client.get('/customers')
      setCustomers(data)
      setErrorGeneral('')
    } catch (err) {
      setErrorGeneral(getErrorMessage(err, 'No pudimos cargar los clientes.'))
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

  function openEdit(c) {
    setForm({
      name: c.name,
      email: c.email ?? '',
      phone: c.phone ?? '',
      address: c.address ?? '',
    })
    setErrores({})
    setError('')
    setModal(c)
  }

  function actualizar(campo, valor) {
    setForm((f) => ({ ...f, [campo]: valor }))
    if (REGLAS[campo] && errores[campo]) {
      setErrores((e) => ({ ...e, [campo]: REGLAS[campo](valor) }))
    }
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
    const body = { ...form, address: form.address.trim() || null }
    try {
      if (modal === 'create') {
        await client.post('/customers', body)
      } else {
        await client.put(`/customers/${modal.id}`, body)
      }
      setModal(null)
      load()
    } catch (err) {
      // El modal sigue abierto con los datos cargados para poder corregirlos.
      setError(getErrorMessage(err, 'No pudimos guardar el cliente.'))
      setErrores((previos) => ({ ...previos, ...getFieldErrors(err) }))
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(c) {
    if (!confirm(`¿Eliminar al cliente «${c.name}»?`)) return
    try {
      await client.delete(`/customers/${c.id}`)
      setErrorGeneral('')
      load()
    } catch (err) {
      setErrorGeneral(getErrorMessage(err, 'No pudimos eliminar el cliente.'))
    }
  }

  async function openHistory(id) {
    setHistory({ loading: true })
    try {
      const { data } = await client.get(`/customers/${id}/orders`)
      setHistory(data)
    } catch (err) {
      setHistory(null)
      setErrorGeneral(getErrorMessage(err, 'No pudimos cargar el historial.'))
    }
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-bold text-tx-primary">Clientes</h1>
        <button
          onClick={openCreate}
          className="rounded-lg bg-secondary px-4 py-2 text-sm font-medium text-secondary-text transition hover:bg-secondary-dark"
        >
          + Nuevo cliente
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
            <table className="w-full min-w-[520px] text-sm">
              <thead className="border-b border-brand-border bg-sidebar text-xs uppercase tracking-wide text-tx-muted">
                <tr>
                  {['Nombre', 'Correo', 'Teléfono', 'Dirección', ''].map((h) => (
                    <th key={h} className="px-4 py-3 text-left font-medium">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {customers.map((c) => (
                  <tr key={c.id}>
                    <td className="px-4 py-3 font-medium text-tx-primary">{c.name}</td>
                    <td className="px-4 py-3 text-tx-secondary">{c.email ?? '—'}</td>
                    <td className="px-4 py-3 text-tx-secondary">{c.phone ?? '—'}</td>
                    <td className="max-w-xs truncate px-4 py-3 text-tx-secondary">
                      {c.address ?? '—'}
                    </td>
                    <td className="space-x-3 whitespace-nowrap px-4 py-3 text-right">
                      <button
                        onClick={() => openHistory(c.id)}
                        className="text-xs text-tx-muted hover:underline"
                      >
                        Pedidos
                      </button>
                      <button
                        onClick={() => openEdit(c)}
                        className="text-xs text-primary-text hover:underline"
                      >
                        Editar
                      </button>
                      <button
                        onClick={() => handleDelete(c)}
                        className="text-xs text-danger hover:underline"
                      >
                        Eliminar
                      </button>
                    </td>
                  </tr>
                ))}
                {customers.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-4 py-6 text-center text-tx-muted">
                      Todavía no hay clientes.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Alta / edición */}
      {modal && (
        <Modal
          title={modal === 'create' ? 'Nuevo cliente' : 'Editar cliente'}
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
                onBlur={() =>
                  REGLAS[key] &&
                  setErrores((x) => ({ ...x, [key]: REGLAS[key](form[key]) }))
                }
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

      {/* Historial de pedidos */}
      {history && (
        <Modal
          title={`Pedidos — ${history.customer?.name ?? ''}`}
          onClose={() => setHistory(null)}
        >
          {history.loading ? (
            <p className="text-sm text-tx-muted">Cargando…</p>
          ) : history.orders?.length === 0 ? (
            <p className="text-sm text-tx-muted">Este cliente todavía no tiene pedidos.</p>
          ) : (
            <div className="space-y-4">
              {history.orders.map((o) => (
                <div key={o.id} className="rounded-lg border border-brand-border p-4">
                  <div className="mb-2 flex items-center justify-between">
                    <span className="text-sm font-medium text-tx-primary">Pedido n.º {o.id}</span>
                    <div className="flex items-center gap-3">
                      <Badge value={o.status} />
                      <span className="text-xs text-tx-muted">
                        {new Date(o.created_at).toLocaleDateString()}
                      </span>
                    </div>
                  </div>
                  <table className="w-full text-xs">
                    <tbody className="divide-y divide-gray-50">
                      {o.items.map((i) => (
                        <tr key={i.product_id}>
                          <td className="py-1 text-tx-secondary">{i.product_name}</td>
                          <td className="py-1 font-mono text-tx-muted">{i.product_sku}</td>
                          <td className="py-1 text-right text-tx-secondary">
                            {parseFloat(i.quantity)} × ${parseFloat(i.unit_price).toFixed(2)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <p className="mt-2 text-right text-sm font-semibold text-tx-primary">
                    Total: ${parseFloat(o.total).toFixed(2)}
                  </p>
                </div>
              ))}
            </div>
          )}
        </Modal>
      )}
    </div>
  )
}
