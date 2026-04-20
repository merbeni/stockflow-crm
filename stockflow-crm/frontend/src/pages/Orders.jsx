import { useEffect, useState } from 'react'
import client from '../api/client'
import Badge from '../components/ui/Badge'
import Modal from '../components/ui/Modal'

const STATUS_LABEL = { pending: 'processing', processing: 'shipped', shipped: 'delivered' }

export default function Orders() {
  const [orders, setOrders] = useState([])
  const [loading, setLoading] = useState(true)
  const [customers, setCustomers] = useState([])
  const [products, setProducts] = useState([])

  // Create order modal
  const [createModal, setCreateModal] = useState(false)
  const [customerId, setCustomerId] = useState('')

  // Add item modal
  const [itemModal, setItemModal] = useState(null) // order object
  const [itemForm, setItemForm] = useState({ product_id: '', quantity: '', unit_price: '' })
  const [itemError, setItemError] = useState('')
  const [itemSaving, setItemSaving] = useState(false)

  async function load() {
    setLoading(true)
    const { data } = await client.get('/orders')
    setOrders(data)
    setLoading(false)
  }

  useEffect(() => {
    load()
    client.get('/customers').then(r => setCustomers(r.data))
    client.get('/products').then(r => setProducts(r.data))
  }, [])

  async function handleCreate(e) {
    e.preventDefault()
    try {
      await client.post('/orders', { customer_id: parseInt(customerId) })
      setCreateModal(false)
      setCustomerId('')
      load()
    } catch (err) {
      alert(err.response?.data?.detail ?? 'Error creating order.')
    }
  }

  async function handleDelete(id) {
    if (!confirm('Delete this order?')) return
    try {
      await client.delete(`/orders/${id}`)
      load()
    } catch (err) {
      alert(err.response?.data?.detail ?? 'Cannot delete order.')
    }
  }

  async function handleAdvance(id) {
    try {
      await client.post(`/orders/${id}/advance`)
      load()
    } catch (err) {
      alert(err.response?.data?.detail ?? 'Cannot advance order.')
    }
  }

  function openAddItem(order) {
    setItemForm({ product_id: '', quantity: '', unit_price: '' })
    setItemError('')
    setItemModal(order)
  }

  async function handleAddItem(e) {
    e.preventDefault()
    setItemError('')
    setItemSaving(true)
    try {
      await client.post(`/orders/${itemModal.id}/items`, {
        product_id: parseInt(itemForm.product_id),
        quantity: parseFloat(itemForm.quantity),
        unit_price: parseFloat(itemForm.unit_price),
      })
      setItemModal(null)
      load()
    } catch (err) {
      setItemError(err.response?.data?.detail ?? 'Error adding item.')
    } finally {
      setItemSaving(false)
    }
  }

  async function handleRemoveItem(orderId, itemId) {
    try {
      await client.delete(`/orders/${orderId}/items/${itemId}`)
      load()
    } catch (err) {
      alert(err.response?.data?.detail ?? 'Cannot remove item.')
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold text-tx-primary">Orders</h1>
        <button onClick={() => setCreateModal(true)} className="bg-secondary text-secondary-text px-4 py-2 rounded-lg text-sm font-medium hover:bg-secondary-dark transition">+ New order</button>
      </div>

      {loading ? (
        <p className="text-sm text-tx-muted">Loading…</p>
      ) : (
        <div className="space-y-4">
          {orders.length === 0 && <p className="text-sm text-tx-muted">No orders yet.</p>}
          {orders.map(o => (
            <div key={o.id} className="bg-surface rounded-xl shadow border border-brand-border p-5">
              <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
                <div className="flex items-center gap-3">
                  <span className="font-semibold text-tx-primary">Order #{o.id}</span>
                  <Badge value={o.status} />
                  <span className="text-xs text-tx-muted">{new Date(o.created_at).toLocaleDateString()}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-sm text-tx-secondary">{o.customer_name}</span>
                  {STATUS_LABEL[o.status] && (
                    <button onClick={() => handleAdvance(o.id)} className="text-xs bg-primary text-primary-text hover:bg-primary-dark px-2 py-1 rounded-md font-medium">
                      Mark {STATUS_LABEL[o.status]}
                    </button>
                  )}
                  {o.status === 'pending' && (
                    <>
                      <button onClick={() => openAddItem(o)} className="text-xs bg-sidebar hover:bg-brand-border px-2 py-1 rounded-md text-tx-secondary">+ Item</button>
                      <button onClick={() => handleDelete(o.id)} className="text-xs text-red-500 hover:underline">Delete</button>
                    </>
                  )}
                </div>
              </div>

              {o.items.length > 0 ? (
                <div className="overflow-x-auto">
                <table className="w-full min-w-[420px] text-sm">
                  <thead className="text-xs text-tx-muted border-b border-brand-border">
                    <tr>
                      {['Product', 'SKU', 'Qty', 'Unit price', 'Subtotal', ''].map(h => (
                        <th key={h} className="pb-1 text-left font-medium">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {o.items.map(i => (
                      <tr key={i.id}>
                        <td className="py-1.5 text-tx-primary">{i.product_name}</td>
                        <td className="py-1.5 font-mono text-xs text-tx-muted">{i.product_sku}</td>
                        <td className="py-1.5 text-tx-secondary">{parseFloat(i.quantity)}</td>
                        <td className="py-1.5 text-tx-secondary">${parseFloat(i.unit_price).toFixed(2)}</td>
                        <td className="py-1.5 text-tx-secondary">${(parseFloat(i.quantity) * parseFloat(i.unit_price)).toFixed(2)}</td>
                        <td className="py-1.5 text-right">
                          {o.status === 'pending' && (
                            <button onClick={() => handleRemoveItem(o.id, i.id)} className="text-xs text-red-400 hover:text-red-600">Remove</button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                </div>
              ) : (
                <p className="text-xs text-tx-muted">No items yet.</p>
              )}

              <p className="text-right font-semibold text-sm mt-2 text-tx-primary">Total: ${parseFloat(o.total).toFixed(2)}</p>
            </div>
          ))}
        </div>
      )}

      {/* Create order modal */}
      {createModal && (
        <Modal title="New order" onClose={() => setCreateModal(false)}>
          <form onSubmit={handleCreate} className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-tx-secondary mb-1">Customer</label>
              <select required value={customerId} onChange={e => setCustomerId(e.target.value)} className="w-full border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary">
                <option value="">Select customer…</option>
                {customers.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button type="button" onClick={() => setCreateModal(false)} className="px-4 py-1.5 text-sm rounded-lg border border-gray-300 hover:bg-sidebar">Cancel</button>
              <button type="submit" disabled={!customerId} className="px-4 py-1.5 text-sm rounded-lg bg-secondary text-secondary-text hover:bg-secondary-dark disabled:opacity-50 disabled:cursor-not-allowed">Create</button>
            </div>
          </form>
        </Modal>
      )}

      {/* Add item modal */}
      {itemModal && (
        <Modal title={`Add item — Order #${itemModal.id}`} onClose={() => setItemModal(null)} disabled={itemSaving}>
          <form onSubmit={handleAddItem} className="space-y-3">
            {itemError && <p className="text-xs text-red-600 bg-red-50 rounded px-2 py-1">{itemError}</p>}
            <div>
              <label className="block text-xs font-medium text-tx-secondary mb-1">Product</label>
              <select required disabled={itemSaving} value={itemForm.product_id} onChange={e => {
                const p = products.find(p => p.id === parseInt(e.target.value))
                setItemForm(f => ({ ...f, product_id: e.target.value, unit_price: p ? parseFloat(p.price).toFixed(2) : '' }))
              }} className="w-full border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary disabled:bg-gray-50 disabled:text-tx-muted">
                <option value="">Select product…</option>
                {products.filter(p => p.is_active).map(p => <option key={p.id} value={p.id}>{p.name} ({p.sku}) — stock: {parseFloat(p.current_stock)}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-tx-secondary mb-1">Quantity</label>
              <input type="number" step="any" min="0.001" required disabled={itemSaving} value={itemForm.quantity} onChange={e => setItemForm(f => ({ ...f, quantity: e.target.value }))} className="w-full border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary disabled:bg-gray-50 disabled:text-tx-muted" />
              {itemForm.product_id && (() => {
                const p = products.find(p => p.id === parseInt(itemForm.product_id))
                if (!p) return null
                const stock = parseFloat(p.current_stock)
                const qty = parseFloat(itemForm.quantity)
                const over = qty > stock
                return (
                  <p className={`text-xs mt-1 ${over ? 'text-red-500' : 'text-tx-muted'}`}>
                    {over ? `Exceeds available stock — ` : 'Available: '}
                    <strong>{stock}</strong> units
                  </p>
                )
              })()}
            </div>
            <div>
              <label className="block text-xs font-medium text-tx-secondary mb-1">Unit price</label>
              <input type="number" step="any" min="0" required disabled={itemSaving} value={itemForm.unit_price} onChange={e => setItemForm(f => ({ ...f, unit_price: e.target.value }))} className="w-full border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary disabled:bg-gray-50 disabled:text-tx-muted" />
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button type="button" onClick={() => setItemModal(null)} disabled={itemSaving} className="px-4 py-1.5 text-sm rounded-lg border border-gray-300 hover:bg-sidebar disabled:opacity-50">Cancel</button>
              <button type="submit" disabled={itemSaving} className="px-4 py-1.5 text-sm rounded-lg bg-secondary text-secondary-text hover:bg-secondary-dark disabled:opacity-50 disabled:cursor-not-allowed min-w-[80px]">
                {itemSaving ? 'Adding…' : 'Add'}
              </button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  )
}
