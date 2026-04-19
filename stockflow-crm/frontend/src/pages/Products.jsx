import { useEffect, useState } from 'react'
import client from '../api/client'
import Modal from '../components/ui/Modal'

const EMPTY = { sku: '', name: '', description: '', price: '', current_stock: '', minimum_stock: '' }

export default function Products() {
  const [products, setProducts] = useState([])
  const [modal, setModal] = useState(null) // null | 'create' | product object
  const [form, setForm] = useState(EMPTY)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  async function load() {
    setLoading(true)
    const { data } = await client.get('/products')
    setProducts(data)
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  function openCreate() { setForm(EMPTY); setError(''); setModal('create') }
  function openEdit(p) {
    setForm({ sku: p.sku, name: p.name, description: p.description ?? '', price: p.price, current_stock: p.current_stock, minimum_stock: p.minimum_stock })
    setError('')
    setModal(p)
  }

  async function handleSave(e) {
    e.preventDefault()
    setError('')
    setSaving(true)
    const body = { ...form, price: parseFloat(form.price), current_stock: parseFloat(form.current_stock), minimum_stock: parseFloat(form.minimum_stock) }
    try {
      if (modal === 'create') {
        await client.post('/products', body)
      } else {
        await client.put(`/products/${modal.id}`, body)
      }
      setModal(null)
      load()
    } catch (err) {
      setError(err.response?.data?.detail ?? 'Error saving product.')
    } finally {
      setSaving(false)
    }
  }

  async function handleToggleActive(p) {
    try {
      await client.put(`/products/${p.id}`, { is_active: !p.is_active })
      load()
    } catch (err) {
      setError(err.response?.data?.detail ?? 'Could not update product.')
      setModal('error')
    }
  }

  async function handleDelete(id) {
    if (!confirm('Delete this product?')) return
    try {
      await client.delete(`/products/${id}`)
      load()
    } catch (err) {
      setError(err.response?.data?.detail ?? 'Cannot delete product.')
      setModal('error')
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold text-tx-primary">Products</h1>
        <button onClick={openCreate} className="bg-secondary text-secondary-text px-4 py-2 rounded-lg text-sm font-medium hover:bg-secondary-dark transition">+ New product</button>
      </div>

      {loading ? (
        <p className="text-sm text-tx-muted">Loading…</p>
      ) : (
        <div className="bg-surface rounded-xl shadow overflow-hidden border border-brand-border">
          <table className="w-full text-sm">
            <thead className="bg-sidebar border-b border-brand-border text-xs text-tx-muted uppercase tracking-wide">
              <tr>
                {['SKU', 'Name', 'Price', 'Stock', 'Min stock', ''].map(h => (
                  <th key={h} className="px-4 py-3 text-left font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {products.map(p => (
                <tr key={p.id} className={!p.is_active ? 'opacity-50 bg-gray-50' : p.low_stock ? 'bg-red-50' : ''}>
                  <td className="px-4 py-3 font-mono text-xs text-tx-secondary">{p.sku}</td>
                  <td className="px-4 py-3 font-medium text-tx-primary">
                    {p.name}
                    {p.low_stock && p.is_active && <span className="ml-2 text-xs text-red-500 font-normal">low stock</span>}
                    {!p.is_active && <span className="ml-2 text-xs text-tx-muted font-normal">inactive</span>}
                  </td>
                  <td className="px-4 py-3 text-tx-secondary">${parseFloat(p.price).toFixed(2)}</td>
                  <td className="px-4 py-3 text-tx-secondary">{parseFloat(p.current_stock)}</td>
                  <td className="px-4 py-3 text-tx-secondary">{parseFloat(p.minimum_stock)}</td>
                  <td className="px-4 py-3 text-right space-x-3">
                    <button onClick={() => openEdit(p)} className="text-primary-text hover:underline text-xs">Edit</button>
                    <button onClick={() => handleToggleActive(p)} className={`text-xs hover:underline ${p.is_active ? 'text-amber-500' : 'text-green-600'}`}>
                      {p.is_active ? 'Deactivate' : 'Activate'}
                    </button>
                    <button onClick={() => handleDelete(p.id)} className="text-red-500 hover:underline text-xs">Delete</button>
                  </td>
                </tr>
              ))}
              {products.length === 0 && (
                <tr><td colSpan={6} className="px-4 py-6 text-center text-tx-muted">No products yet.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {modal === 'error' && (
        <Modal title="Cannot delete product" onClose={() => setModal(null)}>
          <p className="text-sm text-tx-secondary">{error}</p>
          <div className="flex justify-end mt-4">
            <button onClick={() => setModal(null)} className="px-4 py-1.5 text-sm rounded-lg bg-secondary text-secondary-text hover:bg-secondary-dark">OK</button>
          </div>
        </Modal>
      )}

      {modal && modal !== 'error' && (
        <Modal title={modal === 'create' ? 'New product' : 'Edit product'} onClose={() => setModal(null)} disabled={saving}>
          <form onSubmit={handleSave} className="space-y-3">
            {error && <p className="text-xs text-red-600 bg-red-50 rounded px-2 py-1">{error}</p>}
            {[
              { key: 'sku', label: 'SKU', type: 'text', disabled: modal !== 'create' },
              { key: 'name', label: 'Name', type: 'text' },
              { key: 'description', label: 'Description', type: 'text' },
              { key: 'price', label: 'Price', type: 'number' },
              { key: 'current_stock', label: 'Current stock', type: 'number' },
              { key: 'minimum_stock', label: 'Minimum stock', type: 'number' },
            ].map(({ key, label, type, disabled }) => (
              <div key={key}>
                <label className="block text-xs font-medium text-tx-secondary mb-1">{label}</label>
                <input
                  type={type}
                  step="any"
                  disabled={disabled || saving}
                  value={form[key]}
                  onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
                  className="w-full border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary disabled:bg-gray-50 disabled:text-tx-muted"
                />
              </div>
            ))}
            <div className="flex justify-end gap-2 pt-2">
              <button type="button" onClick={() => setModal(null)} disabled={saving} className="px-4 py-1.5 text-sm rounded-lg border border-gray-300 hover:bg-sidebar disabled:opacity-50">Cancel</button>
              <button
                type="submit"
                disabled={saving || !form.sku.trim() || !form.name.trim() || form.price === '' || form.current_stock === '' || form.minimum_stock === ''}
                className="px-4 py-1.5 text-sm rounded-lg bg-secondary text-secondary-text hover:bg-secondary-dark disabled:opacity-50 disabled:cursor-not-allowed min-w-[80px]"
              >
                {saving ? 'Saving…' : 'Save'}
              </button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  )
}
