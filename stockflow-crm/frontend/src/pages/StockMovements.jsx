import { useEffect, useState } from 'react'
import client from '../api/client'
import Badge from '../components/ui/Badge'
import Modal from '../components/ui/Modal'

export default function StockMovements() {
  const [movements, setMovements] = useState([])
  const [loading, setLoading] = useState(true)
  const [detail, setDetail] = useState(null)
  const [detailLoading, setDetailLoading] = useState(false)

  // Filters
  const [typeFilter, setTypeFilter] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')

  async function load() {
    setLoading(true)
    const params = {}
    if (typeFilter) params.type = typeFilter
    if (dateFrom) params.date_from = new Date(dateFrom + 'T00:00:00').toISOString()
    if (dateTo) params.date_to = new Date(dateTo + 'T23:59:59').toISOString()
    const { data } = await client.get('/stock-movements', { params })
    setMovements(data)
    setLoading(false)
  }

  useEffect(() => { load() }, [typeFilter, dateFrom, dateTo])

  async function openDetail(id) {
    setDetailLoading(true)
    setDetail({})
    const { data } = await client.get(`/stock-movements/${id}`)
    setDetail(data)
    setDetailLoading(false)
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold text-tx-primary">Stock Movements</h1>
      </div>

      {/* Filters */}
      <div className="flex gap-3 mb-4 flex-wrap">
        <select value={typeFilter} onChange={e => setTypeFilter(e.target.value)} className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary">
          <option value="">All types</option>
          <option value="entry">Entry</option>
          <option value="exit">Sale</option>
          <option value="adjustment">Adjustment</option>
        </select>
        <label className="flex items-center gap-2 text-sm text-tx-secondary">
          From
          <input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)} className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary" />
        </label>
        <label className="flex items-center gap-2 text-sm text-tx-secondary">
          To
          <input type="date" value={dateTo} onChange={e => setDateTo(e.target.value)} className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary" />
        </label>
        {(typeFilter || dateFrom || dateTo) && (
          <button onClick={() => { setTypeFilter(''); setDateFrom(''); setDateTo('') }} className="text-xs text-tx-muted hover:text-tx-secondary underline">Clear</button>
        )}
      </div>

      {loading ? (
        <p className="text-sm text-tx-muted">Loading…</p>
      ) : (
        <div className="bg-surface rounded-xl shadow overflow-hidden border border-brand-border">
          <div className="overflow-x-auto">
          <table className="w-full min-w-[520px] text-sm">
            <thead className="bg-sidebar border-b border-brand-border text-xs text-tx-muted uppercase tracking-wide">
              <tr>
                {['Date', 'Product', 'Type', 'Quantity', 'Origin', ''].map(h => (
                  <th key={h} className="px-4 py-3 text-left font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {movements.map(m => (
                <tr key={m.id}>
                  <td className="px-4 py-3 text-tx-muted whitespace-nowrap">{new Date(m.created_at).toLocaleDateString()}</td>
                  <td className="px-4 py-3 font-medium text-tx-primary">{m.product.name}<br /><span className="text-xs text-tx-muted font-mono">{m.product.sku}</span></td>
                  <td className="px-4 py-3"><Badge value={m.type} /></td>
                  <td className="px-4 py-3">
                    {m.type === 'adjustment'
                      ? <span className={parseFloat(m.quantity) >= 0 ? 'text-green-600' : 'text-red-500'}>
                          {parseFloat(m.quantity) >= 0 ? '+' : ''}{parseFloat(m.quantity)}
                        </span>
                      : parseFloat(m.quantity)
                    }
                  </td>
                  <td className="px-4 py-3 text-tx-muted text-xs">
                    {m.invoice ? `Invoice #${m.invoice_id} · ${m.invoice.supplier_name ?? ''}` : ''}
                    {m.order ? `Order #${m.order_id} · ${m.order.customer_name ?? ''}` : ''}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button onClick={() => openDetail(m.id)} className="text-primary-text hover:underline text-xs">Detail</button>
                  </td>
                </tr>
              ))}
              {movements.length === 0 && (
                <tr><td colSpan={6} className="px-4 py-6 text-center text-tx-muted">No movements found.</td></tr>
              )}
            </tbody>
          </table>
          </div>
        </div>
      )}

      {detail !== null && (
        <Modal title={`Movement detail`} onClose={() => setDetail(null)}>
          {detailLoading ? (
            <p className="text-sm text-tx-muted">Loading…</p>
          ) : (
            <div className="space-y-4 text-sm">
              <div className="flex gap-4 flex-wrap">
                <div><span className="text-tx-muted">Product:</span> <span className="font-medium text-tx-primary">{detail.product?.name}</span></div>
                <div><span className="text-tx-muted">SKU:</span> <span className="font-mono text-xs text-tx-secondary">{detail.product?.sku}</span></div>
                <div><span className="text-tx-muted">Type:</span> <Badge value={detail.type} /></div>
                <div><span className="text-tx-muted">Quantity:</span>{' '}
                  {detail.type === 'adjustment'
                    ? <span className={parseFloat(detail.quantity) >= 0 ? 'text-green-600 font-medium' : 'text-red-500 font-medium'}>
                        {parseFloat(detail.quantity) >= 0 ? '+' : ''}{parseFloat(detail.quantity)}
                      </span>
                    : parseFloat(detail.quantity ?? 0)
                  }
                </div>
                <div><span className="text-tx-muted">Date:</span> {detail.created_at ? new Date(detail.created_at).toLocaleString() : ''}</div>
              </div>

              {detail.invoice && (
                <div>
                  <p className="font-medium text-tx-primary mb-2">Invoice #{detail.invoice_id} — {detail.invoice.supplier_name ?? 'Unknown supplier'}</p>
                  <p className="text-xs text-tx-muted mb-2">Status: <Badge value={detail.invoice.status} /></p>
                  {detail.invoice.items?.length > 0 && (
                    <table className="w-full text-xs border border-brand-border rounded-lg overflow-hidden">
                      <thead className="bg-sidebar text-tx-muted">
                        <tr>
                          {['Description', 'Qty', 'Unit price', 'Confidence', 'Status'].map(h => (
                            <th key={h} className="px-3 py-2 text-left">{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {detail.invoice.items.map(item => (
                          <tr key={item.id} className={item.skipped ? 'bg-gray-50 opacity-60' : ''}>
                            <td className={`px-3 py-2 ${item.skipped ? 'line-through text-tx-muted' : 'text-tx-primary'}`}>{item.description}</td>
                            <td className="px-3 py-2 text-tx-muted">{item.skipped ? '—' : parseFloat(item.quantity)}</td>
                            <td className="px-3 py-2 text-tx-muted">{item.skipped ? '—' : `$${parseFloat(item.unit_price).toFixed(2)}`}</td>
                            <td className="px-3 py-2">{item.skipped ? '—' : <Badge value={item.confidence} />}</td>
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
                  {detail.invoice.gemini_raw && (
                    <details className="mt-3">
                      <summary className="text-xs text-tx-muted cursor-pointer hover:text-tx-secondary">Raw Gemini JSON</summary>
                      <pre className="mt-2 text-xs bg-sidebar rounded p-3 overflow-auto max-h-48">{JSON.stringify(detail.invoice.gemini_raw, null, 2)}</pre>
                    </details>
                  )}
                </div>
              )}

              {detail.order && (
                <div>
                  <p className="font-medium text-tx-primary">Order #{detail.order_id} — {detail.order.customer_name}</p>
                  <p className="text-xs text-tx-muted mt-1">Status: <Badge value={detail.order.status} /></p>
                </div>
              )}
            </div>
          )}
        </Modal>
      )}
    </div>
  )
}
