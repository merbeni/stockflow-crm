import { useEffect, useState } from 'react'
import client from '../api/client'
import Modal from '../components/ui/Modal'

const EMPTY = { name: '', contact_name: '', email: '', phone: '' }

export default function Suppliers() {
  const [suppliers, setSuppliers] = useState([])
  const [modal, setModal] = useState(null)
  const [form, setForm] = useState(EMPTY)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  async function load() {
    setLoading(true)
    const { data } = await client.get('/suppliers')
    setSuppliers(data)
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  function openCreate() { setForm(EMPTY); setError(''); setModal('create') }
  function openEdit(s) {
    setForm({ name: s.name, contact_name: s.contact_name ?? '', email: s.email ?? '', phone: s.phone ?? '' })
    setError('')
    setModal(s)
  }

  async function handleSave(e) {
    e.preventDefault()
    setError('')
    try {
      if (modal === 'create') {
        await client.post('/suppliers', form)
      } else {
        await client.put(`/suppliers/${modal.id}`, form)
      }
      setModal(null)
      load()
    } catch (err) {
      setError(err.response?.data?.detail ?? 'Error saving supplier.')
    }
  }

  async function handleDelete(id) {
    if (!confirm('Delete this supplier?')) return
    try {
      await client.delete(`/suppliers/${id}`)
      load()
    } catch (err) {
      alert(err.response?.data?.detail ?? 'Cannot delete supplier.')
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold text-tx-primary">Suppliers</h1>
        <button onClick={openCreate} className="bg-secondary text-secondary-text px-4 py-2 rounded-lg text-sm font-medium hover:bg-secondary-dark transition">+ New supplier</button>
      </div>

      {loading ? (
        <p className="text-sm text-tx-muted">Loading…</p>
      ) : (
        <div className="bg-surface rounded-xl shadow overflow-hidden border border-brand-border">
          <div className="overflow-x-auto">
          <table className="w-full min-w-[480px] text-sm">
            <thead className="bg-sidebar border-b border-brand-border text-xs text-tx-muted uppercase tracking-wide">
              <tr>
                {['Name', 'Contact', 'Email', 'Phone', ''].map(h => (
                  <th key={h} className="px-4 py-3 text-left font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {suppliers.map(s => (
                <tr key={s.id}>
                  <td className="px-4 py-3 font-medium text-tx-primary">{s.name}</td>
                  <td className="px-4 py-3 text-tx-secondary">{s.contact_name ?? '—'}</td>
                  <td className="px-4 py-3 text-tx-secondary">{s.email ?? '—'}</td>
                  <td className="px-4 py-3 text-tx-secondary">{s.phone ?? '—'}</td>
                  <td className="px-4 py-3 text-right space-x-3">
                    <button onClick={() => openEdit(s)} className="text-primary-text hover:underline text-xs">Edit</button>
                    <button onClick={() => handleDelete(s.id)} className="text-red-500 hover:underline text-xs">Delete</button>
                  </td>
                </tr>
              ))}
              {suppliers.length === 0 && (
                <tr><td colSpan={5} className="px-4 py-6 text-center text-tx-muted">No suppliers yet.</td></tr>
              )}
            </tbody>
          </table>
          </div>
        </div>
      )}

      {modal && (
        <Modal title={modal === 'create' ? 'New supplier' : 'Edit supplier'} onClose={() => setModal(null)}>
          <form onSubmit={handleSave} className="space-y-3">
            {error && <p className="text-xs text-red-600 bg-red-50 rounded px-2 py-1">{error}</p>}
            {[
              { key: 'name', label: 'Name', required: true },
              { key: 'contact_name', label: 'Contact name', required: true },
              { key: 'email', label: 'Email', type: 'email', required: true },
              { key: 'phone', label: 'Phone' },
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
                disabled={!form.name.trim() || !form.contact_name.trim() || !form.email.trim()}
                className="px-4 py-1.5 text-sm rounded-lg bg-secondary text-secondary-text hover:bg-secondary-dark disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Save
              </button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  )
}
