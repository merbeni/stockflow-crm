import { useEffect, useState } from 'react'
import client from '../api/client'
import { getErrorMessage } from '../api/errors'
import Badge from '../components/ui/Badge'
import ErrorBanner from '../components/ui/ErrorBanner'
import Modal from '../components/ui/Modal'

const hoy = () => new Date().toISOString().slice(0, 10)

export default function StockMovements() {
  const [movements, setMovements] = useState([])
  const [loading, setLoading] = useState(true)
  const [detail, setDetail] = useState(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [error, setError] = useState('')

  // Filtros
  const [typeFilter, setTypeFilter] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')

  // Un rango invertido devolvía una lista vacía sin explicación: ahora se avisa
  // antes de consultar y el backend lo rechaza con un 400 explícito.
  const rangoInvertido = Boolean(dateFrom && dateTo && dateFrom > dateTo)

  async function load() {
    if (rangoInvertido) {
      // El aviso del rango invertido se muestra aparte. Si además quedaba un
      // error del servidor de la consulta anterior, se apilaban dos carteles
      // rojos diciendo cosas distintas sobre el mismo filtro.
      setError('')
      return
    }
    setLoading(true)
    const params = {}
    if (typeFilter) params.type = typeFilter
    if (dateFrom) params.date_from = new Date(dateFrom + 'T00:00:00').toISOString()
    if (dateTo) params.date_to = new Date(dateTo + 'T23:59:59').toISOString()
    try {
      const { data } = await client.get('/stock-movements', { params })
      setMovements(data)
      setError('')
    } catch (err) {
      setError(getErrorMessage(err, 'No pudimos cargar los movimientos.'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [typeFilter, dateFrom, dateTo])

  async function openDetail(id) {
    setDetailLoading(true)
    setDetail({})
    try {
      const { data } = await client.get(`/stock-movements/${id}`)
      setDetail(data)
    } catch (err) {
      setDetail(null)
      setError(getErrorMessage(err, 'No pudimos cargar el detalle.'))
    } finally {
      setDetailLoading(false)
    }
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-bold text-tx-primary">Movimientos de stock</h1>
      </div>

      {/* Filtros */}
      <div className="mb-2 flex flex-wrap gap-3">
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          aria-label="Filtrar por tipo"
          className="rounded-lg border border-input-border px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-secondary"
        >
          <option value="">Todos los tipos</option>
          <option value="entry">Entrada</option>
          <option value="exit">Venta</option>
          <option value="adjustment">Ajuste</option>
        </select>

        <label className="flex items-center gap-2 text-sm text-tx-secondary">
          Desde
          <input
            type="date"
            value={dateFrom}
            max={dateTo || hoy()}
            onChange={(e) => setDateFrom(e.target.value)}
            className={`rounded-lg border px-3 py-1.5 text-sm focus:outline-none focus:ring-2 ${
              rangoInvertido
                ? 'border-danger focus:ring-danger'
                : 'border-input-border focus:ring-secondary'
            }`}
          />
        </label>

        <label className="flex items-center gap-2 text-sm text-tx-secondary">
          Hasta
          <input
            type="date"
            value={dateTo}
            min={dateFrom || undefined}
            onChange={(e) => setDateTo(e.target.value)}
            className={`rounded-lg border px-3 py-1.5 text-sm focus:outline-none focus:ring-2 ${
              rangoInvertido
                ? 'border-danger focus:ring-danger'
                : 'border-input-border focus:ring-secondary'
            }`}
          />
        </label>

        {(typeFilter || dateFrom || dateTo) && (
          <button
            onClick={() => {
              setTypeFilter('')
              setDateFrom('')
              setDateTo('')
            }}
            className="text-xs text-tx-muted underline hover:text-tx-secondary"
          >
            Limpiar filtros
          </button>
        )}
      </div>

      {rangoInvertido && (
        <p role="alert" className="mb-4 text-xs text-danger">
          La fecha «desde» no puede ser posterior a la fecha «hasta». Corregí el
          rango para ver los resultados.
        </p>
      )}

      <ErrorBanner message={error} className="mb-4" onDismiss={() => setError('')} />

      {loading ? (
        <p className="text-sm text-tx-muted">Cargando…</p>
      ) : (
        <div className="overflow-hidden rounded-xl border border-brand-border bg-surface shadow">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[560px] text-sm">
              <thead className="border-b border-brand-border bg-sidebar text-xs uppercase tracking-wide text-tx-muted">
                <tr>
                  {['Fecha', 'Producto', 'Tipo', 'Cantidad', 'Origen', ''].map((h) => (
                    <th key={h} className="px-4 py-3 text-left font-medium">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {movements.map((m) => (
                  <tr key={m.id}>
                    <td className="whitespace-nowrap px-4 py-3 text-tx-muted">
                      {new Date(m.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3 font-medium text-tx-primary">
                      {m.product.name}
                      <br />
                      <span className="font-mono text-xs text-tx-muted">{m.product.sku}</span>
                    </td>
                    <td className="px-4 py-3">
                      <Badge value={m.type} />
                    </td>
                    <td className="px-4 py-3">
                      {m.type === 'adjustment' ? (
                        <span
                          className={
                            parseFloat(m.quantity) >= 0 ? 'text-success' : 'text-danger'
                          }
                        >
                          {parseFloat(m.quantity) >= 0 ? '+' : ''}
                          {parseFloat(m.quantity)}
                        </span>
                      ) : (
                        parseFloat(m.quantity)
                      )}
                    </td>
                    <td className="px-4 py-3 text-xs text-tx-muted">
                      {m.invoice
                        ? `Factura n.º ${m.invoice_id} · ${m.invoice.supplier_name ?? ''}`
                        : ''}
                      {m.order
                        ? `Pedido n.º ${m.order_id} · ${m.order.customer_name ?? ''}`
                        : ''}
                      {!m.invoice && !m.order ? 'Carga manual' : ''}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() => openDetail(m.id)}
                        className="text-xs text-primary-text hover:underline"
                      >
                        Detalle
                      </button>
                    </td>
                  </tr>
                ))}
                {movements.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-4 py-6 text-center text-tx-muted">
                      No se encontraron movimientos con esos filtros.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {detail !== null && (
        <Modal title="Detalle del movimiento" onClose={() => setDetail(null)}>
          {detailLoading ? (
            <p className="text-sm text-tx-muted">Cargando…</p>
          ) : (
            <div className="space-y-4 text-sm">
              <div className="flex flex-wrap gap-4">
                <div>
                  <span className="text-tx-muted">Producto:</span>{' '}
                  <span className="font-medium text-tx-primary">{detail.product?.name}</span>
                </div>
                <div>
                  <span className="text-tx-muted">SKU:</span>{' '}
                  <span className="font-mono text-xs text-tx-secondary">
                    {detail.product?.sku}
                  </span>
                </div>
                <div>
                  <span className="text-tx-muted">Tipo:</span> <Badge value={detail.type} />
                </div>
                <div>
                  <span className="text-tx-muted">Cantidad:</span>{' '}
                  {detail.type === 'adjustment' ? (
                    <span
                      className={
                        parseFloat(detail.quantity) >= 0
                          ? 'font-medium text-success'
                          : 'font-medium text-danger'
                      }
                    >
                      {parseFloat(detail.quantity) >= 0 ? '+' : ''}
                      {parseFloat(detail.quantity)}
                    </span>
                  ) : (
                    parseFloat(detail.quantity ?? 0)
                  )}
                </div>
                <div>
                  <span className="text-tx-muted">Fecha:</span>{' '}
                  {detail.created_at ? new Date(detail.created_at).toLocaleString() : ''}
                </div>
              </div>

              {detail.invoice && (
                <div>
                  <p className="mb-2 font-medium text-tx-primary">
                    Factura n.º {detail.invoice_id} —{' '}
                    {detail.invoice.supplier_name ?? 'Proveedor sin identificar'}
                  </p>
                  <p className="mb-2 text-xs text-tx-muted">
                    Estado: <Badge value={detail.invoice.status} />
                  </p>
                  {detail.invoice.items?.length > 0 && (
                    <table className="w-full overflow-hidden rounded-lg border border-brand-border text-xs">
                      <thead className="bg-sidebar text-tx-muted">
                        <tr>
                          {['Descripción', 'Cant.', 'Precio unit.', 'Confianza', 'Estado'].map(
                            (h) => (
                              <th key={h} className="px-3 py-2 text-left">
                                {h}
                              </th>
                            )
                          )}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {detail.invoice.items.map((item) => (
                          <tr key={item.id} className={item.skipped ? 'bg-gray-50 opacity-60' : ''}>
                            <td
                              className={`px-3 py-2 ${
                                item.skipped ? 'text-tx-muted line-through' : 'text-tx-primary'
                              }`}
                            >
                              {item.description}
                            </td>
                            <td className="px-3 py-2 text-tx-muted">
                              {item.skipped ? '—' : parseFloat(item.quantity)}
                            </td>
                            <td className="px-3 py-2 text-tx-muted">
                              {item.skipped
                                ? '—'
                                : `$${parseFloat(item.unit_price).toFixed(2)}`}
                            </td>
                            <td className="px-3 py-2">
                              {item.skipped ? '—' : <Badge value={item.confidence} />}
                            </td>
                            <td className="px-3 py-2">
                              {item.skipped ? (
                                <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-500">
                                  Omitida
                                </span>
                              ) : (
                                <span className="inline-flex items-center rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">
                                  Sumada al stock
                                </span>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              )}

              {detail.order && (
                <div>
                  <p className="mb-1 font-medium text-tx-primary">
                    Pedido n.º {detail.order_id} —{' '}
                    {detail.order.customer_name ?? 'Cliente sin identificar'}
                  </p>
                  <p className="text-xs text-tx-muted">
                    Estado: <Badge value={detail.order.status} />
                  </p>
                </div>
              )}

              {!detail.invoice && !detail.order && (
                <p className="text-xs text-tx-muted">
                  Movimiento generado manualmente desde la ficha del producto.
                </p>
              )}
            </div>
          )}
        </Modal>
      )}
    </div>
  )
}
