import { useEffect, useState } from 'react'
import client from '../api/client'
import { getErrorMessage, getFieldErrors } from '../api/errors'
import Badge from '../components/ui/Badge'
import ErrorBanner from '../components/ui/ErrorBanner'
import FormField from '../components/ui/FormField'
import Modal from '../components/ui/Modal'
import { cantidadStock, numeroNoNegativo, requerido } from '../utils/validation'

// Siguiente estado del flujo y su etiqueta en español.
const SIGUIENTE_ESTADO = {
  pending: 'en preparación',
  processing: 'enviado',
  shipped: 'entregado',
}

export default function Orders() {
  const [orders, setOrders] = useState([])
  const [loading, setLoading] = useState(true)
  const [customers, setCustomers] = useState([])
  const [products, setProducts] = useState([])
  const [error, setError] = useState('')

  // Alta de pedido
  const [createModal, setCreateModal] = useState(false)
  const [customerId, setCustomerId] = useState('')
  const [createError, setCreateError] = useState('')

  // Alta de línea
  const [itemModal, setItemModal] = useState(null)
  const [itemForm, setItemForm] = useState({ product_id: '', quantity: '', unit_price: '' })
  const [itemErrores, setItemErrores] = useState({})
  const [itemError, setItemError] = useState('')
  const [itemSaving, setItemSaving] = useState(false)

  async function load() {
    setLoading(true)
    try {
      const { data } = await client.get('/orders')
      setOrders(data)
      setError('')
    } catch (err) {
      setError(getErrorMessage(err, 'No pudimos cargar los pedidos.'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    client.get('/customers').then((r) => setCustomers(r.data)).catch(() => {})
    client.get('/products').then((r) => setProducts(r.data)).catch(() => {})
  }, [])

  const productoElegido = products.find((p) => p.id === parseInt(itemForm.product_id, 10))
  const permiteDecimales = Boolean(productoElegido?.allow_decimal_stock)

  async function handleCreate(e) {
    e.preventDefault()
    setCreateError('')
    try {
      await client.post('/orders', { customer_id: parseInt(customerId, 10) })
      setCreateModal(false)
      setCustomerId('')
      load()
    } catch (err) {
      setCreateError(getErrorMessage(err, 'No pudimos crear el pedido.'))
    }
  }

  async function handleDelete(o) {
    if (!confirm(`¿Eliminar el pedido n.º ${o.id}?`)) return
    try {
      await client.delete(`/orders/${o.id}`)
      setError('')
      load()
    } catch (err) {
      setError(getErrorMessage(err, 'No pudimos eliminar el pedido.'))
    }
  }

  async function handleAdvance(o) {
    try {
      await client.post(`/orders/${o.id}/advance`)
      setError('')
      load()
    } catch (err) {
      setError(getErrorMessage(err, 'No pudimos avanzar el estado del pedido.'))
    }
  }

  function openAddItem(order) {
    setItemForm({ product_id: '', quantity: '', unit_price: '' })
    setItemErrores({})
    setItemError('')
    setItemModal(order)
  }

  function validarItem(valores, producto) {
    const errores = {}
    const faltaProducto = requerido(valores.product_id)
    if (faltaProducto) errores.product_id = 'Elegí un producto.'

    const cantidadInvalida = cantidadStock(
      valores.quantity,
      Boolean(producto?.allow_decimal_stock)
    )
    if (cantidadInvalida) errores.quantity = cantidadInvalida
    else if (Number(valores.quantity) <= 0) errores.quantity = 'Debe ser mayor que cero.'
    else if (producto && Number(valores.quantity) > parseFloat(producto.current_stock)) {
      errores.quantity = `Supera el stock disponible (${parseFloat(producto.current_stock)}).`
    }

    const precioInvalido = numeroNoNegativo(valores.unit_price)
    if (precioInvalido) errores.unit_price = precioInvalido

    return errores
  }

  async function handleAddItem(e) {
    e.preventDefault()
    setItemError('')

    const encontrados = validarItem(itemForm, productoElegido)
    setItemErrores(encontrados)
    if (Object.keys(encontrados).length > 0) {
      setItemError('Revisá los campos marcados antes de agregar la línea.')
      return
    }

    setItemSaving(true)
    try {
      await client.post(`/orders/${itemModal.id}/items`, {
        product_id: parseInt(itemForm.product_id, 10),
        quantity: parseFloat(itemForm.quantity),
        unit_price: parseFloat(itemForm.unit_price),
      })
      setItemModal(null)
      load()
    } catch (err) {
      setItemError(getErrorMessage(err, 'No pudimos agregar el producto.'))
      setItemErrores((previos) => ({ ...previos, ...getFieldErrors(err) }))
    } finally {
      setItemSaving(false)
    }
  }

  async function handleRemoveItem(orderId, itemId) {
    try {
      await client.delete(`/orders/${orderId}/items/${itemId}`)
      setError('')
      load()
    } catch (err) {
      setError(getErrorMessage(err, 'No pudimos quitar el producto del pedido.'))
    }
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-bold text-tx-primary">Pedidos</h1>
        <button
          onClick={() => {
            setCreateError('')
            setCreateModal(true)
          }}
          className="rounded-lg bg-secondary px-4 py-2 text-sm font-medium text-secondary-text transition hover:bg-secondary-dark"
        >
          + Nuevo pedido
        </button>
      </div>

      <ErrorBanner message={error} className="mb-4" onDismiss={() => setError('')} />

      {loading ? (
        <p className="text-sm text-tx-muted">Cargando…</p>
      ) : (
        <div className="space-y-4">
          {orders.length === 0 && (
            <p className="text-sm text-tx-muted">Todavía no hay pedidos.</p>
          )}
          {orders.map((o) => (
            <div
              key={o.id}
              className="rounded-xl border border-brand-border bg-surface p-5 shadow"
            >
              <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-3">
                  <span className="font-semibold text-tx-primary">Pedido n.º {o.id}</span>
                  <Badge value={o.status} />
                  <span className="text-xs text-tx-muted">
                    {new Date(o.created_at).toLocaleDateString()}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-sm text-tx-secondary">{o.customer_name}</span>
                  {SIGUIENTE_ESTADO[o.status] && (
                    <button
                      onClick={() => handleAdvance(o)}
                      className="rounded-md bg-primary px-2 py-1 text-xs font-medium text-primary-text hover:bg-primary-dark"
                    >
                      Marcar como {SIGUIENTE_ESTADO[o.status]}
                    </button>
                  )}
                  {o.status === 'pending' && (
                    <>
                      <button
                        onClick={() => openAddItem(o)}
                        className="rounded-md bg-sidebar px-2 py-1 text-xs text-tx-secondary hover:bg-brand-border"
                      >
                        + Producto
                      </button>
                      <button
                        onClick={() => handleDelete(o)}
                        className="text-xs text-red-500 hover:underline"
                      >
                        Eliminar
                      </button>
                    </>
                  )}
                </div>
              </div>

              {o.items.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[420px] text-sm">
                    <thead className="border-b border-brand-border text-xs text-tx-muted">
                      <tr>
                        {['Producto', 'SKU', 'Cant.', 'Precio unit.', 'Subtotal', ''].map((h) => (
                          <th key={h} className="pb-1 text-left font-medium">
                            {h}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-50">
                      {o.items.map((i) => (
                        <tr key={i.id}>
                          <td className="py-1.5 text-tx-primary">{i.product_name}</td>
                          <td className="py-1.5 font-mono text-xs text-tx-muted">
                            {i.product_sku}
                          </td>
                          <td className="py-1.5 text-tx-secondary">{parseFloat(i.quantity)}</td>
                          <td className="py-1.5 text-tx-secondary">
                            ${parseFloat(i.unit_price).toFixed(2)}
                          </td>
                          <td className="py-1.5 text-tx-secondary">
                            $
                            {(parseFloat(i.quantity) * parseFloat(i.unit_price)).toFixed(2)}
                          </td>
                          <td className="py-1.5 text-right">
                            {o.status === 'pending' && (
                              <button
                                onClick={() => handleRemoveItem(o.id, i.id)}
                                className="text-xs text-red-400 hover:text-red-600"
                              >
                                Quitar
                              </button>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="text-xs text-tx-muted">Este pedido todavía no tiene productos.</p>
              )}

              <p className="mt-2 text-right text-sm font-semibold text-tx-primary">
                Total: ${parseFloat(o.total).toFixed(2)}
              </p>
            </div>
          ))}
        </div>
      )}

      {/* Alta de pedido */}
      {createModal && (
        <Modal title="Nuevo pedido" onClose={() => setCreateModal(false)}>
          <form onSubmit={handleCreate} noValidate className="space-y-3">
            <ErrorBanner message={createError} />
            <FormField name="customer_id" label="Cliente" required>
              <select
                id="campo-customer_id"
                required
                value={customerId}
                onChange={(e) => setCustomerId(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              >
                <option value="">Elegí un cliente…</option>
                {customers.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </FormField>
            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setCreateModal(false)}
                className="rounded-lg border border-gray-300 px-4 py-1.5 text-sm hover:bg-sidebar"
              >
                Cancelar
              </button>
              <button
                type="submit"
                disabled={!customerId}
                className="rounded-lg bg-secondary px-4 py-1.5 text-sm text-secondary-text hover:bg-secondary-dark disabled:cursor-not-allowed disabled:opacity-50"
              >
                Crear
              </button>
            </div>
          </form>
        </Modal>
      )}

      {/* Alta de línea */}
      {itemModal && (
        <Modal
          title={`Agregar producto — Pedido n.º ${itemModal.id}`}
          onClose={() => setItemModal(null)}
          disabled={itemSaving}
        >
          <form onSubmit={handleAddItem} noValidate className="space-y-3">
            <ErrorBanner message={itemError} />

            <FormField
              name="product_id"
              label="Producto"
              required
              error={itemErrores.product_id}
            >
              <select
                id="campo-product_id"
                disabled={itemSaving}
                value={itemForm.product_id}
                onChange={(e) => {
                  const p = products.find((x) => x.id === parseInt(e.target.value, 10))
                  setItemForm((f) => ({
                    ...f,
                    product_id: e.target.value,
                    unit_price: p ? parseFloat(p.price).toFixed(2) : '',
                  }))
                  setItemErrores({})
                }}
                className={`w-full rounded-lg border px-3 py-1.5 text-sm focus:outline-none focus:ring-2 disabled:bg-gray-50 disabled:text-tx-muted ${
                  itemErrores.product_id
                    ? 'border-red-400 focus:ring-red-300'
                    : 'border-gray-300 focus:ring-primary'
                }`}
              >
                <option value="">Elegí un producto…</option>
                {products
                  .filter((p) => p.is_active)
                  .map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} ({p.sku}) — stock: {parseFloat(p.current_stock)}
                    </option>
                  ))}
              </select>
            </FormField>

            <FormField
              name="quantity"
              label="Cantidad"
              type="number"
              // Los productos por unidad no admiten cantidades fraccionarias.
              step={permiteDecimales ? '0.001' : '1'}
              min={permiteDecimales ? '0.001' : '1'}
              required
              disabled={itemSaving}
              value={itemForm.quantity}
              error={itemErrores.quantity}
              hint={
                productoElegido
                  ? `Disponible: ${parseFloat(productoElegido.current_stock)}${
                      permiteDecimales ? ' (admite decimales)' : ' (unidades enteras)'
                    }`
                  : undefined
              }
              onChange={(e) => {
                setItemForm((f) => ({ ...f, quantity: e.target.value }))
                setItemErrores((x) => ({ ...x, quantity: undefined }))
              }}
              onBlur={() =>
                setItemErrores((x) => ({
                  ...x,
                  ...validarItem(itemForm, productoElegido),
                }))
              }
            />

            <FormField
              name="unit_price"
              label="Precio unitario"
              type="number"
              step="0.01"
              min="0"
              required
              disabled={itemSaving}
              value={itemForm.unit_price}
              error={itemErrores.unit_price}
              onChange={(e) => {
                setItemForm((f) => ({ ...f, unit_price: e.target.value }))
                setItemErrores((x) => ({ ...x, unit_price: undefined }))
              }}
            />

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setItemModal(null)}
                disabled={itemSaving}
                className="rounded-lg border border-gray-300 px-4 py-1.5 text-sm hover:bg-sidebar disabled:opacity-50"
              >
                Cancelar
              </button>
              <button
                type="submit"
                disabled={itemSaving}
                className="min-w-[90px] rounded-lg bg-secondary px-4 py-1.5 text-sm text-secondary-text hover:bg-secondary-dark disabled:cursor-not-allowed disabled:opacity-50"
              >
                {itemSaving ? 'Agregando…' : 'Agregar'}
              </button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  )
}
