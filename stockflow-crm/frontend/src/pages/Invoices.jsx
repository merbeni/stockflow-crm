import { useEffect, useRef, useState } from 'react'
import client from '../api/client'
import Badge from '../components/ui/Badge'
import Modal from '../components/ui/Modal'

// ── Upload step ───────────────────────────────────────────────────────────────
function UploadStep({ onProcessed }) {
  const [file, setFile] = useState(null)
  const [previewUrl, setPreviewUrl] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [retrying, setRetrying] = useState(false)
  const [countdown, setCountdown] = useState(0)
  const [error, setError] = useState('')
  const inputRef = useRef()
  const countdownRef = useRef(null)

  function pickFile(picked) {
    if (previewUrl) URL.revokeObjectURL(previewUrl)
    setFile(picked ?? null)
    setPreviewUrl(picked ? URL.createObjectURL(picked) : null)
    setError('')
  }

  useEffect(() => () => { if (previewUrl) URL.revokeObjectURL(previewUrl) }, [])

  function startCountdown(seconds, onDone) {
    setCountdown(seconds)
    let remaining = seconds
    countdownRef.current = setInterval(() => {
      remaining -= 1
      setCountdown(remaining)
      if (remaining <= 0) {
        clearInterval(countdownRef.current)
        onDone()
      }
    }, 1000)
  }

  async function sendRequest(form) {
    const { data } = await client.post('/invoices/process', form)
    return data
  }

  async function handleUpload(e) {
    e.preventDefault()
    if (!file) return
    setError('')
    setRetrying(false)
    setUploading(true)

    const form = new FormData()
    form.append('file', file)

    try {
      const data = await sendRequest(form)
      onProcessed(data)
    } catch (firstErr) {
      const isGeminiDown = firstErr.response?.status === 503 &&
        firstErr.response?.data?.detail === 'gemini_unavailable'

      if (!isGeminiDown) {
        setError(firstErr.response?.data?.detail ?? 'Processing failed.')
        setUploading(false)
        return
      }

      // Gemini 503 — show countdown, then retry once
      setRetrying(true)
      startCountdown(5, async () => {
        setRetrying(false)
        try {
          const data = await sendRequest(form)
          onProcessed(data)
        } catch {
          setError(
            'Gemini is still under heavy demand. Please wait a few minutes and try again.'
          )
          setUploading(false)
        }
      })
    }
  }

  const buttonLabel = retrying
    ? `Gemini is busy — retrying in ${countdown}s…`
    : uploading
    ? 'Processing with Gemini…'
    : 'Process invoice'

  return (
    <div className="max-w-md">
      <h2 className="text-base font-semibold text-tx-secondary mb-4">Upload invoice</h2>
      <form onSubmit={handleUpload} className="space-y-4">
        <div
          onClick={() => inputRef.current.click()}
          className="border-2 border-dashed border-brand-border rounded-xl p-8 text-center cursor-pointer hover:border-primary-dark transition"
        >
          {file ? (
            <>
              <p className="text-sm text-tx-muted">File selected</p>
              <p className="text-xs text-primary-text mt-1">Click to change</p>
            </>
          ) : (
            <>
              <p className="text-sm text-tx-muted">Click to select a PDF, JPG, or PNG</p>
              <p className="text-xs text-tx-muted mt-1">Max 20 MB</p>
            </>
          )}
          <input
            ref={inputRef}
            type="file"
            accept=".pdf,.jpg,.jpeg,.png"
            className="hidden"
            onChange={e => pickFile(e.target.files[0])}
          />
        </div>

        {previewUrl && !uploading && !retrying && (
          <div className="rounded-xl border border-brand-border overflow-hidden bg-sidebar">
            {file.type === 'application/pdf' ? (
              <iframe
                src={previewUrl}
                title="Invoice preview"
                className="w-full h-72"
              />
            ) : (
              <img
                src={previewUrl}
                alt="Invoice preview"
                className="w-full max-h-72 object-contain"
              />
            )}
            <div className="px-3 py-2 border-t border-brand-border flex items-center justify-between">
              <p className="text-xs text-tx-muted truncate">{file.name}</p>
              <button
                type="button"
                onClick={() => pickFile(null)}
                className="text-xs text-red-500 hover:underline ml-3 shrink-0"
              >
                Remove
              </button>
            </div>
          </div>
        )}

        {retrying && (
          <div className="flex items-center gap-2 bg-amber-50 border border-amber-200 rounded-lg px-4 py-3">
            <svg className="w-4 h-4 text-amber-500 shrink-0 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
            </svg>
            <p className="text-sm text-amber-700">
              Gemini AI is experiencing high demand — retrying automatically in <strong>{countdown}s</strong>…
            </p>
          </div>
        )}

        {error && <p className="text-xs text-red-600 bg-red-50 rounded px-3 py-2">{error}</p>}

        <button
          type="submit"
          disabled={!file || uploading || retrying}
          className="bg-secondary text-secondary-text px-5 py-2 rounded-lg text-sm font-medium hover:bg-secondary-dark disabled:opacity-50 transition"
        >
          {buttonLabel}
        </button>
      </form>
    </div>
  )
}

// ── Review / confirm step ─────────────────────────────────────────────────────
function ReviewStep({ processed, products, suppliers, onConfirmed, onCancel }) {
  // Per-item state
  const [items, setItems] = useState(() =>
    processed.items.map(item => ({
      invoice_item_id: item.id,
      // Convert to string so the <select> value comparison works correctly
      product_id: item.suggested_product_id ? String(item.suggested_product_id) : '',
      use_new: false,
      new_product: { sku: '', name: item.description, description: '', price: parseFloat(item.unit_price).toFixed(2), minimum_stock: '0' },
      // Only pre-fill supplier SKU when a product is also pre-selected
      supplier_sku: item.suggested_product_id ? (item.suggested_supplier_sku ?? '') : '',
      skip: false,
    }))
  )

  // Supplier combobox state — pre-fill from Gemini result
  const [supplierQuery, setSupplierQuery] = useState(processed.supplier ?? '')
  const [supplierDropdownOpen, setSupplierDropdownOpen] = useState(false)
  const [selectedSupplier, setSelectedSupplier] = useState(
    // Auto-select if Gemini already matched one
    processed.supplier_id ? suppliers.find(s => s.id === processed.supplier_id) ?? null : null
  )
  const [newSupplierForm, setNewSupplierForm] = useState({ contact_name: '', email: '', phone: '' })

  const isNewSupplier = !selectedSupplier && supplierQuery.trim() !== ''
  const newSupplierComplete = isNewSupplier
    ? newSupplierForm.contact_name.trim() !== '' && newSupplierForm.email.trim() !== ''
    : true

  const supplierMatches = supplierQuery.trim()
    ? suppliers.filter(s => s.name.toLowerCase().includes(supplierQuery.toLowerCase()))
    : suppliers

  function pickSupplier(s) {
    setSelectedSupplier(s)
    setSupplierQuery(s.name)
    setNewSupplierForm({ contact_name: '', email: '', phone: '' })
    setSupplierDropdownOpen(false)
  }

  function clearSupplier() {
    setSelectedSupplier(null)
    setSupplierQuery('')
    setNewSupplierForm({ contact_name: '', email: '', phone: '' })
  }

  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  function setItem(idx, patch) {
    setItems(prev => prev.map((it, i) => i === idx ? { ...it, ...patch } : it))
  }

  async function handleConfirm() {
    setError('')
    setSubmitting(true)

    // Resolve supplier for payload
    const supplierPayload = selectedSupplier
      ? { supplier_id: selectedSupplier.id }
      : supplierQuery.trim()
      ? { new_supplier: { name: supplierQuery.trim(), ...newSupplierForm } }
      : {}

    const payload = {
      ...supplierPayload,
      items: items.map(it => {
        if (it.skip) return { invoice_item_id: it.invoice_item_id, skip: true }
        if (it.use_new) {
          const np = it.new_product
          return {
            invoice_item_id: it.invoice_item_id,
            new_product: {
              sku: np.sku,
              name: np.name,
              description: np.description || null,
              price: parseFloat(np.price),
              minimum_stock: parseFloat(np.minimum_stock),
            },
            supplier_sku: it.supplier_sku || null,
          }
        }
        return {
          invoice_item_id: it.invoice_item_id,
          product_id: parseInt(it.product_id),
          supplier_sku: it.supplier_sku || null,
        }
      }),
    }
    try {
      await client.post(`/invoices/${processed.invoice_id}/confirm`, payload)
      onConfirmed()
    } catch (err) {
      setError(err.response?.data?.detail ?? 'Confirm failed.')
    } finally {
      setSubmitting(false)
    }
  }

  async function handleReject() {
    if (!confirm('Reject this invoice?')) return
    await client.post(`/invoices/${processed.invoice_id}/reject`)
    onCancel()
  }

  return (
    <div className="max-w-3xl">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-base font-semibold text-tx-secondary">Review — Invoice #{processed.invoice_id}</h2>
          <p className="text-xs text-tx-muted mt-0.5">{processed.date ?? 'No date'}</p>
        </div>
        <div className="flex gap-2">
          <button onClick={handleReject} className="text-sm px-3 py-1.5 rounded-lg border border-red-300 text-red-600 hover:bg-red-50">Reject</button>
          <button onClick={handleConfirm} disabled={submitting || !newSupplierComplete} className="text-sm px-4 py-1.5 rounded-lg bg-secondary text-secondary-text hover:bg-secondary-dark disabled:opacity-50 disabled:cursor-not-allowed">
            {submitting ? 'Confirming…' : 'Confirm & update stock'}
          </button>
        </div>
      </div>

      {/* Supplier combobox */}
      <div className="bg-surface border border-brand-border rounded-xl p-4 mb-4">
        <label className="block text-xs font-medium text-tx-muted mb-1.5">Supplier</label>
        <div className="relative">
          <input
            type="text"
            value={supplierQuery}
            onChange={e => { setSupplierQuery(e.target.value); setSelectedSupplier(null); setSupplierDropdownOpen(true) }}
            onFocus={() => setSupplierDropdownOpen(true)}
            onBlur={() => setTimeout(() => setSupplierDropdownOpen(false), 150)}
            placeholder="Type to search or create…"
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
          />
          {supplierDropdownOpen && (
            <div className="absolute z-10 mt-1 w-full bg-surface border border-brand-border rounded-lg shadow-lg max-h-48 overflow-auto">
              {supplierMatches.length > 0 ? (
                supplierMatches.map(s => (
                  <button
                    key={s.id}
                    type="button"
                    onMouseDown={() => pickSupplier(s)}
                    className="w-full text-left px-3 py-2 text-sm hover:bg-primary hover:text-primary-text"
                  >
                    {s.name}
                  </button>
                ))
              ) : (
                <p className="px-3 py-2 text-xs text-tx-muted">No matches — will create "{supplierQuery}"</p>
              )}
            </div>
          )}
        </div>
        {/* Status / hint below combobox */}
        <p className="mt-1.5 text-xs">
          {selectedSupplier ? (
            <span className="text-green-600">Existing supplier selected
              <button type="button" onClick={clearSupplier} className="ml-2 text-tx-muted hover:text-red-500">✕ clear</button>
            </span>
          ) : supplierQuery.trim() ? (
            <span className="text-amber-600">New supplier — complete the fields below before confirming</span>
          ) : (
            <span className="text-tx-muted">No supplier — leave blank to skip</span>
          )}
        </p>

        {/* New supplier required fields */}
        {isNewSupplier && (
          <div className="mt-3 grid grid-cols-1 gap-2 border-t border-brand-border pt-3">
            <p className="text-xs font-medium text-tx-secondary mb-1">New supplier details <span className="text-red-500">*</span></p>
            {[
              { key: 'contact_name', label: 'Contact name', required: true, type: 'text' },
              { key: 'email',        label: 'Email',         required: true, type: 'email' },
              { key: 'phone',        label: 'Phone',         required: false, type: 'text' },
            ].map(({ key, label, required, type }) => (
              <div key={key} className="flex items-center gap-3">
                <label className="text-xs text-tx-muted w-28 shrink-0">
                  {label}{required && <span className="text-red-500 ml-0.5">*</span>}
                </label>
                <input
                  type={type}
                  required={required}
                  value={newSupplierForm[key]}
                  onChange={e => setNewSupplierForm(f => ({ ...f, [key]: e.target.value }))}
                  className="flex-1 border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                  placeholder={required ? `Required` : 'Optional'}
                />
              </div>
            ))}
          </div>
        )}
      </div>

      {error && <p className="text-xs text-red-600 bg-red-50 rounded px-3 py-2 mb-4">{error}</p>}

      <div className="space-y-3">
        {processed.items.map((item, idx) => {
          const state = items[idx]
          return (
            <div key={item.id} className={`bg-surface border rounded-xl p-4 ${item.confidence !== 'high' ? 'border-yellow-300' : 'border-brand-border'}`}>
              <div className="flex items-start justify-between gap-4 mb-3">
                <div className="flex-1">
                  <p className="font-medium text-sm text-tx-primary">{item.description}</p>
                  <p className="text-xs text-tx-muted mt-0.5">
                    Qty: {parseFloat(item.quantity)} · Unit price (from document): ${parseFloat(item.unit_price).toFixed(2)}
                  </p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <Badge value={item.confidence} />
                  <label className="flex items-center gap-1 text-xs text-tx-muted">
                    <input type="checkbox" checked={state.skip} onChange={e => setItem(idx, { skip: e.target.checked })} />
                    Skip
                  </label>
                </div>
              </div>

              {!state.skip && (
                <div className="space-y-2">
                  {/* Product selection */}
                  <div className="flex gap-2 items-center">
                    <label className="text-xs text-tx-muted w-28 shrink-0">Link to product</label>
                    {!state.use_new ? (
                      <select
                        value={state.product_id}
                        onChange={e => {
                          const pid = e.target.value
                          const autoSku = pid ? (processed.supplier_product_skus?.[parseInt(pid)] ?? '') : ''
                          setItem(idx, { product_id: pid, supplier_sku: autoSku })
                        }}
                        className="flex-1 border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                      >
                        <option value="">Select product…</option>
                        {products.map(p => (
                          <option key={p.id} value={p.id}>{p.name} ({p.sku})</option>
                        ))}
                      </select>
                    ) : (
                      <span className="text-xs text-tx-muted italic">Creating new product below</span>
                    )}
                    <button
                      type="button"
                      onClick={() => setItem(idx, { use_new: !state.use_new, product_id: '' })}
                      className="text-xs text-primary-text hover:underline whitespace-nowrap"
                    >
                      {state.use_new ? '← Use existing' : '+ New product'}
                    </button>
                  </div>

                  {/* New product fields */}
                  {state.use_new && (
                    <div className="grid grid-cols-2 gap-2 bg-sidebar rounded-lg p-3">
                      {[
                        { key: 'sku', label: 'SKU', required: true },
                        { key: 'name', label: 'Name', required: true },
                        { key: 'description', label: 'Description' },
                        { key: 'price', label: 'Price', type: 'number' },
                        { key: 'minimum_stock', label: 'Min stock', type: 'number' },
                      ].map(({ key, label, required, type = 'text' }) => (
                        <div key={key}>
                          <label className="block text-xs text-tx-muted mb-0.5">{label}</label>
                          <input
                            type={type}
                            step="any"
                            required={required}
                            value={state.new_product[key]}
                            onChange={e => setItem(idx, { new_product: { ...state.new_product, [key]: e.target.value } })}
                            className="w-full border border-gray-300 rounded px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-primary"
                          />
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Supplier SKU */}
                  <div className="flex gap-2 items-center">
                    <label className="text-xs text-tx-muted w-28 shrink-0">Supplier SKU</label>
                    <input
                      type="text"
                      placeholder="Optional — for future auto-matching"
                      value={state.supplier_sku}
                      onChange={e => setItem(idx, { supplier_sku: e.target.value })}
                      className="flex-1 border border-gray-300 rounded-lg px-3 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-primary"
                    />
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function Invoices() {
  const [invoices, setInvoices] = useState([])
  const [loading, setLoading] = useState(true)
  const [products, setProducts] = useState([])
  const [suppliers, setSuppliers] = useState([])
  const [step, setStep] = useState('list') // 'list' | 'review'
  const [processed, setProcessed] = useState(null)
  const [detailModal, setDetailModal] = useState(null)

  async function load() {
    setLoading(true)
    const { data } = await client.get('/invoices')
    setInvoices(data)
    setLoading(false)
  }

  useEffect(() => {
    load()
    client.get('/products').then(r => setProducts(r.data))
    client.get('/suppliers').then(r => setSuppliers(r.data))
  }, [])

  function handleProcessed(data) {
    setProcessed(data)
    setStep('review')
  }

  function handleConfirmed() {
    setStep('list')
    setProcessed(null)
    load()
  }

  function handleCancel() {
    setStep('list')
    setProcessed(null)
    load()
  }

  function resumeReview(inv) {
    // Reconstruct a processed-like object from the stored invoice
    setProcessed({
      invoice_id: inv.id,
      supplier: inv.supplier_name ?? null,
      supplier_id: inv.supplier_id ?? null,
      date: inv.date ?? null,
      items: (inv.items ?? []).map(item => ({
        id: item.id,
        description: item.description,
        quantity: item.quantity,
        unit_price: item.unit_price,
        confidence: item.confidence,
        suggested_product_id: null,
        suggested_product_name: null,
      })),
    })
    setStep('review')
  }

  if (step === 'review') {
    return (
      <div>
        <div className="flex items-center gap-3 mb-6">
          <h1 className="text-xl font-bold text-tx-primary">Invoices</h1>
          <span className="text-tx-muted">›</span>
          <span className="text-sm text-tx-muted">Review</span>
        </div>
        <ReviewStep processed={processed} products={products} suppliers={suppliers} onConfirmed={handleConfirmed} onCancel={handleCancel} />
      </div>
    )
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold text-tx-primary">Invoices</h1>
        <button onClick={() => setStep('upload')} className="bg-secondary text-secondary-text px-4 py-2 rounded-lg text-sm font-medium hover:bg-secondary-dark transition">+ Upload invoice</button>
      </div>

      {step === 'upload' && (
        <div className="mb-8 bg-surface rounded-xl shadow border border-brand-border p-6">
          <UploadStep onProcessed={handleProcessed} />
        </div>
      )}

      {loading ? (
        <p className="text-sm text-tx-muted">Loading…</p>
      ) : (
        <div className="bg-surface rounded-xl shadow overflow-hidden border border-brand-border">
          <table className="w-full text-sm">
            <thead className="bg-sidebar border-b border-brand-border text-xs text-tx-muted uppercase tracking-wide">
              <tr>
                {['#', 'Date', 'Supplier', 'Status', 'Items', ''].map(h => (
                  <th key={h} className="px-4 py-3 text-left font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {invoices.map(inv => (
                <tr key={inv.id}>
                  <td className="px-4 py-3 text-tx-muted text-xs">{inv.id}</td>
                  <td className="px-4 py-3 text-tx-secondary">{inv.date ?? '—'}</td>
                  <td className="px-4 py-3 font-medium text-tx-primary">{inv.supplier_name ?? '—'}</td>
                  <td className="px-4 py-3"><Badge value={inv.status} /></td>
                  <td className="px-4 py-3 text-tx-muted">{inv.items?.length ?? 0}</td>
                  <td className="px-4 py-3 text-right space-x-3">
                    {inv.status === 'pending' && (
                      <button onClick={() => resumeReview(inv)} className="text-amber-600 hover:underline text-xs font-medium">Review</button>
                    )}
                    <button onClick={() => setDetailModal(inv)} className="text-primary-text hover:underline text-xs">Detail</button>
                  </td>
                </tr>
              ))}
              {invoices.length === 0 && (
                <tr><td colSpan={6} className="px-4 py-6 text-center text-tx-muted">No invoices yet.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {detailModal && (
        <Modal title={`Invoice #${detailModal.id}`} onClose={() => setDetailModal(null)}>
          <div className="space-y-3 text-sm">
            <div className="flex gap-4 flex-wrap text-sm">
              <span><span className="text-tx-muted">Supplier:</span> {detailModal.supplier_name ?? '—'}</span>
              <span><span className="text-tx-muted">Date:</span> {detailModal.date ?? '—'}</span>
              <span><span className="text-tx-muted">Status:</span> <Badge value={detailModal.status} /></span>
            </div>
            {detailModal.items?.length > 0 && (
              <table className="w-full text-xs border border-brand-border rounded-lg overflow-hidden">
                <thead className="bg-sidebar text-tx-muted">
                  <tr>
                    {['Description', 'Qty', 'Unit price', 'Confidence', 'Supplier SKU', 'Status'].map(h => (
                      <th key={h} className="px-3 py-2 text-left">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {detailModal.items.map(item => (
                    <tr key={item.id} className={item.skipped ? 'bg-gray-50 opacity-60' : ''}>
                      <td className={`px-3 py-2 ${item.skipped ? 'line-through text-tx-muted' : 'text-tx-primary'}`}>{item.description}</td>
                      <td className="px-3 py-2 text-tx-muted">{item.skipped ? '—' : parseFloat(item.quantity)}</td>
                      <td className="px-3 py-2 text-tx-muted">{item.skipped ? '—' : `$${parseFloat(item.unit_price).toFixed(2)}`}</td>
                      <td className="px-3 py-2">{item.skipped ? '—' : <Badge value={item.confidence} />}</td>
                      <td className="px-3 py-2 font-mono text-tx-muted">{item.skipped ? '—' : (item.supplier_sku ?? '—')}</td>
                      <td className="px-3 py-2">
                        {item.skipped
                          ? <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-500">Skipped</span>
                          : <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700">Added to stock</span>
                        }
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </Modal>
      )}
    </div>
  )
}
