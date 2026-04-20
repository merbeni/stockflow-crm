import { useEffect, useState } from 'react'
import client from '../api/client'
import Badge from '../components/ui/Badge'
import Modal from '../components/ui/Modal'

const EMPTY = { name: '', email: '', phone: '', address: '' }

export default function Customers() {
  const [customers, setCustomers] = useState([])
  const [modal, setModal] = useState(null)
  const [form, setForm] = useState(EMPTY)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [history, setHistory] = useState(null) // { customer, orders }

  async function load() {
    setLoading(true)
    const { data } = await client.get('/customers')
    setCustomers(data)
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  function openCreate() { setForm(EMPTY); setError(''); setModal('create') }
  function openEdit(c) {
    setForm({ name: c.name, email: c.email ?? '', phone: c.phone ?? '', address: c.address ?? '' })
    setError('')
    setModal(c)
  }

  async function handleSave(e) {
    e.preventDefault()
    setError('')
    try {
      if (modal === 'create') {
        await client.post('/customers', form)
      } else {
        await client.put(`/customers/${modal.id}`, form)
      }
      setModal(null)
      load()
    } catch (err) {
      setError(err.response?.data?.detail ?? 'Error saving customer.')
    }
  }

  async function handleDelete(id) {
    if (!confirm('Delete this customer?')) return
    try {
      await client.delete(`/customers/${id}`)
      load()
    } catch (err) {
      alert(err.response?.data?.detail ?? 'Cannot delete customer.')
    }
  }

  async function openHistory(id) {
    setHistory({ loading: true })
    const { data } = await client.get(`/customers/${id}/orders`)
    setHistory(data)
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold text-tx-primary">Customers</h1>
        <button onClick={openCreate} className="bg-secondary text-secondary-text px-4 py-2 rounded-lg text-sm font-medium hover:bg-secondary-dark transition">+ New customer</button>
      </div>

      {loading ? (
        <p className="text-sm text-tx-muted">Loading…</p>
      ) : (
        <div className="bg-surface rounded-xl shadow overflow-hidden border border-brand-border">
          <div className="overflow-x-auto">
          <table className="w-full min-w-[520px] text-sm">
            <thead className="bg-sidebar border-b border-brand-border text-xs text-tx-muted uppercase tracking-wide">
              <tr>
                {['Name', 'Email', 'Phone', 'Address', ''].map(h => (
                  <th key={h} className="px-4 py-3 text-left font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {customers.map(c => (
                <tr key={c.id}>
                  <td className="px-4 py-3 font-medium text-tx-primary">{c.name}</td>
                  <td className="px-4 py-3 text-tx-secondary">{c.email ?? '—'}</td>
                  <td className="px-4 py-3 text-tx-secondary">{c.phone ?? '—'}</td>
                  <td className="px-4 py-3 text-tx-secondary max-w-xs truncate">{c.address ?? '—'}</td>
                  <td className="px-4 py-3 text-right space-x-3 whitespace-nowrap">
                    <button onClick={() => openHistory(c.id)} className="text-tx-muted hover:underline text-xs">Orders</button>
                    <button onClick={() => openEdit(c)} className="text-primary-text hover:underline text-xs">Edit</button>
                    <button onClick={() => handleDelete(c.id)} className="text-red-500 hover:underline text-xs">Delete</button>
                  </td>
                </tr>
              ))}
              {customers.length === 0 && (
                <tr><td colSpan={5} className="px-4 py-6 text-center text-tx-muted">No customers yet.</td></tr>
              )}
            </tbody>
          </table>
          </div>
        </div>
      )}

      {/* Create / Edit modal */}
      {modal && (
        <Modal title={modal === 'create' ? 'New customer' : 'Edit customer'} onClose={() => setModal(null)}>
          <form onSubmit={handleSave} className="space-y-3">
            {error && <p className="text-xs text-red-600 bg-red-50 rounded px-2 py-1">{error}</p>}
            {[
              { key: 'name', label: 'Name', required: true },
              { key: 'email', label: 'Email', type: 'email', required: true },
              { key: 'phone', label: 'Phone', required: true },
              { key: 'address', label: 'Address' },
            ].map(({ key, label, required, type = 'text' }) => (
              <div key={key}>
                <label className="block text-xs font-medium text-tx-secondary mb-1">
                  {label}{required && <span className="text-red-500 ml-0.5">*</span>}
                </label>
                <input
                  type={type}
                  required={required}
                  value={form[key]}
                  onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
                  className="w-full border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
            ))}
            <div className="flex justify-end gap-2 pt-2">
              <button type="button" onClick={() => setModal(null)} className="px-4 py-1.5 text-sm rounded-lg border border-gray-300 hover:bg-sidebar">Cancel</button>
              <button
                type="submit"
                disabled={!form.name.trim() || !form.email.trim() || !form.phone.trim()}
                className="px-4 py-1.5 text-sm rounded-lg bg-secondary text-secondary-text hover:bg-secondary-dark disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Save
              </button>
            </div>
          </form>
        </Modal>
      )}

      {/* Order history modal */}
      {history && (
        <Modal title={`Orders — ${history.customer?.name ?? ''}`} onClose={() => setHistory(null)}>
          {history.loading ? (
            <p className="text-sm text-tx-muted">Loading…</p>
          ) : history.orders?.length === 0 ? (
            <p className="text-sm text-tx-muted">No orders yet.</p>
          ) : (
            <div className="space-y-4">
              {history.orders.map(o => (
                <div key={o.id} className="border border-brand-border rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-medium text-tx-primary text-sm">Order #{o.id}</span>
                    <div className="flex items-center gap-3">
                      <Badge value={o.status} />
                      <span className="text-xs text-tx-muted">{new Date(o.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                  <table className="w-full text-xs">
                    <tbody className="divide-y divide-gray-50">
                      {o.items.map(i => (
                        <tr key={i.product_id}>
                          <td className="py-1 text-tx-secondary">{i.product_name}</td>
                          <td className="py-1 text-tx-muted font-mono">{i.product_sku}</td>
                          <td className="py-1 text-right text-tx-secondary">{parseFloat(i.quantity)} × ${parseFloat(i.unit_price).toFixed(2)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <p className="text-right text-sm font-semibold mt-2 text-tx-primary">Total: ${parseFloat(o.total).toFixed(2)}</p>
                </div>
              ))}
            </div>
          )}
        </Modal>
      )}
    </div>
  )
}
