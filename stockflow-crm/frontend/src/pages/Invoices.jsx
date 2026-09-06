import { useEffect, useRef, useState } from 'react'
import client from '../api/client'
import { getErrorMessage } from '../api/errors'
import Badge from '../components/ui/Badge'
import ErrorBanner from '../components/ui/ErrorBanner'
import Modal from '../components/ui/Modal'
import {
  email as validarEmail,
  nombrePersona as validarNombrePersona,
  sku as validarSku,
  telefono as validarTelefono,
} from '../utils/validation'

// ── Paso de carga ─────────────────────────────────────────────────────────────
function UploadStep({ onProcessed, onCancel }) {
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

  useEffect(
    () => () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl)
      if (countdownRef.current) clearInterval(countdownRef.current)
    },
    [previewUrl]
  )

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
      const geminiCaido =
        firstErr.response?.status === 503 &&
        firstErr.response?.data?.detail === 'gemini_unavailable'

      if (!geminiCaido) {
        // Acá aparece el aviso cuando el archivo no es una factura: el backend
        // ya no guarda nada y describe qué detectó realmente.
        setError(getErrorMessage(firstErr, 'No pudimos procesar el archivo.'))
        setUploading(false)
        return
      }

      setRetrying(true)
      startCountdown(5, async () => {
        setRetrying(false)
        try {
          const data = await sendRequest(form)
          onProcessed(data)
        } catch (segundoErr) {
          setError(
            getErrorMessage(
              segundoErr,
              'El servicio de lectura automática sigue con mucha demanda. ' +
                'Esperá unos minutos y volvé a intentar.'
            )
          )
          setUploading(false)
        }
      })
    }
  }

  const etiquetaBoton = retrying
    ? `El servicio está ocupado — reintentando en ${countdown}s…`
    : uploading
    ? 'Procesando con IA…'
    : 'Procesar factura'

  return (
    <div className="max-w-md">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-base font-semibold text-tx-secondary">Subir factura</h2>
        <button
          type="button"
          onClick={onCancel}
          className="text-xs text-tx-muted hover:text-tx-secondary hover:underline"
        >
          Cancelar
        </button>
      </div>

      <form onSubmit={handleUpload} className="space-y-4">
        <div
          onClick={() => inputRef.current.click()}
          className="cursor-pointer rounded-xl border-2 border-dashed border-brand-border p-8 text-center transition hover:border-primary-dark"
        >
          {file ? (
            <>
              <p className="text-sm text-tx-muted">Archivo seleccionado</p>
              <p className="mt-1 text-xs text-primary-text">Hacé clic para cambiarlo</p>
            </>
          ) : (
            <>
              <p className="text-sm text-tx-muted">
                Hacé clic para elegir un PDF, JPG, PNG o WEBP
              </p>
              <p className="mt-1 text-xs text-tx-muted">
                Tiene que ser la factura o el remito del proveedor. Máximo 20 MB.
              </p>
            </>
          )}
          <input
            ref={inputRef}
            type="file"
            accept=".pdf,.jpg,.jpeg,.png,.webp"
            className="hidden"
            onChange={(e) => pickFile(e.target.files[0])}
          />
        </div>

        {previewUrl && !uploading && !retrying && (
          <div className="overflow-hidden rounded-xl border border-brand-border bg-sidebar">
            {file.type === 'application/pdf' ? (
              <iframe src={previewUrl} title="Vista previa de la factura" className="h-72 w-full" />
            ) : (
              <img
                src={previewUrl}
                alt="Vista previa de la factura"
                className="max-h-72 w-full object-contain"
              />
            )}
            <div className="flex items-center justify-between border-t border-brand-border px-3 py-2">
              <p className="truncate text-xs text-tx-muted">{file.name}</p>
              <button
                type="button"
                onClick={() => pickFile(null)}
                className="ml-3 shrink-0 text-xs text-danger hover:underline"
              >
                Quitar
              </button>
            </div>
          </div>
        )}

        {retrying && (
          <div className="flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3">
            <svg className="h-4 w-4 shrink-0 animate-spin text-warning" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
            </svg>
            <p className="text-sm text-amber-700">
              El servicio de IA tiene mucha demanda — reintentamos automáticamente en{' '}
              <strong>{countdown}s</strong>…
            </p>
          </div>
        )}

        <ErrorBanner message={error} onDismiss={() => setError('')} />

        <button
          type="submit"
          disabled={!file || uploading || retrying}
          className="rounded-lg bg-secondary px-5 py-2 text-sm font-medium text-secondary-text transition hover:bg-secondary-dark disabled:opacity-50"
        >
          {etiquetaBoton}
        </button>
      </form>
    </div>
  )
}

// ── Paso de revisión ──────────────────────────────────────────────────────────
function ReviewStep({ processed, products, suppliers, onConfirmed, onCancel, onBack }) {
  const [items, setItems] = useState(() =>
    processed.items.map((item) => ({
      invoice_item_id: item.id,
      // Se convierte a texto para que la comparación del <select> funcione.
      product_id: item.suggested_product_id ? String(item.suggested_product_id) : '',
      use_new: false,
      new_product: {
        sku: '',
        name: item.description,
        description: '',
        price: parseFloat(item.unit_price).toFixed(2),
        minimum_stock: '0',
        allow_decimal_stock: false,
      },
      // El SKU del proveedor solo se precarga si además hay producto sugerido.
      supplier_sku: item.suggested_product_id ? item.suggested_supplier_sku ?? '' : '',
      skip: false,
      // Correcciones manuales de lo que extrajo la IA.
      description: item.description,
      quantity: String(parseFloat(item.quantity)),
      unit_price: parseFloat(item.unit_price).toFixed(2),
    }))
  )

  const [supplierQuery, setSupplierQuery] = useState(processed.supplier ?? '')
  const [supplierDropdownOpen, setSupplierDropdownOpen] = useState(false)
  const [selectedSupplier, setSelectedSupplier] = useState(
    processed.supplier_id
      ? suppliers.find((s) => s.id === processed.supplier_id) ?? null
      : null
  )
  const [newSupplierForm, setNewSupplierForm] = useState({
    contact_name: '',
    email: '',
    phone: '',
  })

  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  const esProveedorNuevo = !selectedSupplier && supplierQuery.trim() !== ''

  /**
   * Errores de formato del proveedor nuevo, campo por campo.
   *
   * Solo se señala un campo que ya tiene contenido: avisar "correo inválido"
   * sobre un campo todavía vacío sería ruido. Lo obligatorio se controla aparte,
   * en `problemasDelProveedor`.
   */
  const erroresProveedor = esProveedorNuevo
    ? {
        contact_name: newSupplierForm.contact_name.trim()
          ? validarNombrePersona(newSupplierForm.contact_name)
          : null,
        email: newSupplierForm.email.trim() ? validarEmail(newSupplierForm.email) : null,
        phone: newSupplierForm.phone.trim() ? validarTelefono(newSupplierForm.phone) : null,
      }
    : {}

  const coincidencias = supplierQuery.trim()
    ? suppliers.filter((s) => s.name.toLowerCase().includes(supplierQuery.toLowerCase()))
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

  function setItem(idx, patch) {
    setItems((prev) => prev.map((it, i) => (i === idx ? { ...it, ...patch } : it)))
  }

  const productoDe = (it) => products.find((p) => p.id === parseInt(it.product_id, 10))

  /** Datos obligatorios y formato del proveedor que se va a crear. */
  function problemasDelProveedor() {
    if (!esProveedorNuevo) return []
    const problemas = []
    const etiquetas = {
      contact_name: 'nombre de contacto',
      email: 'correo',
      phone: 'teléfono',
    }

    if (!newSupplierForm.contact_name.trim()) {
      problemas.push('Proveedor nuevo: falta el nombre de contacto.')
    }
    if (!newSupplierForm.email.trim()) {
      problemas.push('Proveedor nuevo: falta el correo.')
    }
    for (const [campo, mensaje] of Object.entries(erroresProveedor)) {
      if (mensaje) problemas.push(`Proveedor nuevo — ${etiquetas[campo]}: ${mensaje}`)
    }
    return problemas
  }

  /**
   * Valida todas las líneas antes de llamar al backend.
   *
   * Antes no había ninguna comprobación previa: el usuario pulsaba "Confirmar"
   * y recibía un error técnico del servidor.
   */
  function problemasDeLinea() {
    const problemas = []
    items.forEach((it, idx) => {
      if (it.skip) return
      const etiqueta = `Línea ${idx + 1} («${it.description || 'sin descripción'}»)`

      if (!it.use_new && !it.product_id) {
        problemas.push(`${etiqueta}: elegí un producto, creá uno nuevo u omitila.`)
      }
      if (it.use_new) {
        if (!it.new_product.sku.trim()) {
          problemas.push(`${etiqueta}: falta el SKU del producto nuevo.`)
        } else {
          const skuInvalido = validarSku(it.new_product.sku)
          if (skuInvalido) problemas.push(`${etiqueta} — SKU: ${skuInvalido}`)
        }
        if (!it.new_product.name.trim()) problemas.push(`${etiqueta}: falta el nombre del producto nuevo.`)
        if (it.new_product.price === '' || Number(it.new_product.price) < 0) {
          problemas.push(`${etiqueta}: el precio del producto nuevo no es válido.`)
        }
      }

      const cantidad = Number(it.quantity)
      if (!it.quantity || Number.isNaN(cantidad) || cantidad <= 0) {
        problemas.push(`${etiqueta}: la cantidad tiene que ser mayor que cero.`)
      } else {
        const permiteDecimales = it.use_new
          ? it.new_product.allow_decimal_stock
          : Boolean(productoDe(it)?.allow_decimal_stock)
        if (!permiteDecimales && !Number.isInteger(cantidad)) {
          problemas.push(
            `${etiqueta}: el producto se maneja en unidades enteras. Corregí la ` +
              'cantidad o marcalo como producto a granel.'
          )
        }
      }

      if (it.unit_price === '' || Number(it.unit_price) < 0) {
        problemas.push(`${etiqueta}: el precio unitario no es válido.`)
      }
    })
    return problemas
  }

  const problemas = [...problemasDelProveedor(), ...problemasDeLinea()]
  const puedeConfirmar = !submitting && problemas.length === 0 && items.length > 0

  async function handleConfirm() {
    setError('')

    if (problemas.length > 0) {
      setError(problemas.join(' '))
      return
    }

    setSubmitting(true)

    const supplierPayload = selectedSupplier
      ? { supplier_id: selectedSupplier.id }
      : supplierQuery.trim()
      ? { new_supplier: { name: supplierQuery.trim(), ...newSupplierForm } }
      : {}

    const payload = {
      ...supplierPayload,
      items: items.map((it) => {
        if (it.skip) return { invoice_item_id: it.invoice_item_id, skip: true }

        const correcciones = {
          description: it.description,
          quantity: parseFloat(it.quantity),
          unit_price: parseFloat(it.unit_price),
        }

        if (it.use_new) {
          const np = it.new_product
          return {
            invoice_item_id: it.invoice_item_id,
            ...correcciones,
            new_product: {
              sku: np.sku,
              name: np.name,
              description: np.description || null,
              price: parseFloat(np.price),
              minimum_stock: parseFloat(np.minimum_stock || '0'),
              allow_decimal_stock: np.allow_decimal_stock,
            },
            supplier_sku: it.supplier_sku || null,
          }
        }
        return {
          invoice_item_id: it.invoice_item_id,
          ...correcciones,
          product_id: parseInt(it.product_id, 10),
          supplier_sku: it.supplier_sku || null,
        }
      }),
    }

    try {
      await client.post(`/invoices/${processed.invoice_id}/confirm`, payload)
      onConfirmed()
    } catch (err) {
      setError(getErrorMessage(err, 'No pudimos confirmar la factura.'))
    } finally {
      setSubmitting(false)
    }
  }

  async function handleReject() {
    if (
      !confirm(
        'Rechazar la factura la descarta de forma definitiva y no actualiza el stock. ¿Continuar?'
      )
    )
      return
    try {
      await client.post(`/invoices/${processed.invoice_id}/reject`)
      onCancel()
    } catch (err) {
      setError(getErrorMessage(err, 'No pudimos rechazar la factura.'))
    }
  }

  return (
    <div className="max-w-3xl">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-tx-secondary">
            Revisión — Factura n.º {processed.invoice_id}
          </h2>
          <p className="mt-0.5 text-xs text-tx-muted">{processed.date ?? 'Sin fecha'}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {/* Sin este botón el usuario quedaba atrapado en la revisión: las
              únicas salidas eran confirmar o rechazar la factura. */}
          <button
            onClick={onBack}
            disabled={submitting}
            className="rounded-lg border border-input-border px-3 py-1.5 text-sm hover:bg-sidebar disabled:opacity-50"
          >
            ← Volver
          </button>
          <button
            onClick={handleReject}
            disabled={submitting}
            className="rounded-lg border border-red-300 px-3 py-1.5 text-sm text-danger hover:bg-red-50 disabled:opacity-50"
          >
            Rechazar
          </button>
          <button
            onClick={handleConfirm}
            disabled={!puedeConfirmar}
            title={
              problemas.length > 0
                ? 'Hay líneas incompletas: revisá los avisos de abajo.'
                : undefined
            }
            className="rounded-lg bg-secondary px-4 py-1.5 text-sm text-secondary-text hover:bg-secondary-dark disabled:cursor-not-allowed disabled:opacity-50"
          >
            {submitting ? 'Confirmando…' : 'Confirmar y actualizar stock'}
          </button>
        </div>
      </div>

      <p className="mb-4 rounded-lg bg-sidebar px-3 py-2 text-xs text-tx-muted">
        La lectura automática puede equivocarse. Revisá y corregí la descripción,
        la cantidad y el precio de cada línea antes de confirmar. Podés volver
        más tarde: la factura queda pendiente hasta que la confirmes.
      </p>

      {/* Proveedor */}
      <div className="mb-4 rounded-xl border border-brand-border bg-surface p-4">
        <label className="mb-1.5 block text-xs font-medium text-tx-muted">Proveedor</label>
        <div className="relative">
          <input
            type="text"
            value={supplierQuery}
            onChange={(e) => {
              setSupplierQuery(e.target.value)
              setSelectedSupplier(null)
              setSupplierDropdownOpen(true)
            }}
            onFocus={() => setSupplierDropdownOpen(true)}
            onBlur={() => setTimeout(() => setSupplierDropdownOpen(false), 150)}
            placeholder="Escribí para buscar o crear…"
            className="w-full rounded-lg border border-input-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-secondary"
          />
          {supplierDropdownOpen && (
            <div className="absolute z-10 mt-1 max-h-48 w-full overflow-auto rounded-lg border border-brand-border bg-surface shadow-lg">
              {coincidencias.length > 0 ? (
                coincidencias.map((s) => (
                  <button
                    key={s.id}
                    type="button"
                    onMouseDown={() => pickSupplier(s)}
                    className="w-full px-3 py-2 text-left text-sm hover:bg-primary hover:text-primary-text"
                  >
                    {s.name}
                  </button>
                ))
              ) : (
                <p className="px-3 py-2 text-xs text-tx-muted">
                  Sin coincidencias — se creará «{supplierQuery}»
                </p>
              )}
            </div>
          )}
        </div>

        <p className="mt-1.5 text-xs">
          {selectedSupplier ? (
            <span className="text-success">
              Proveedor existente seleccionado
              <button
                type="button"
                onClick={clearSupplier}
                className="ml-2 text-tx-muted hover:text-danger"
              >
                ✕ quitar
              </button>
            </span>
          ) : supplierQuery.trim() ? (
            <span className="text-warning">
              Proveedor nuevo — completá los datos antes de confirmar
            </span>
          ) : (
            <span className="text-tx-muted">Sin proveedor — dejalo vacío para omitirlo</span>
          )}
        </p>

        {esProveedorNuevo && (
          <div className="mt-3 grid grid-cols-1 gap-2 border-t border-brand-border pt-3">
            <p className="mb-1 text-xs font-medium text-tx-secondary">
              Datos del proveedor nuevo <span className="text-danger">*</span>
            </p>
            {[
              { key: 'contact_name', label: 'Nombre de contacto', required: true, type: 'text' },
              { key: 'email', label: 'Correo', required: true, type: 'email' },
              { key: 'phone', label: 'Teléfono', required: false, type: 'text' },
            ].map(({ key, label, required, type }) => (
              <div key={key} className="flex items-start gap-3">
                <label className="w-28 shrink-0 pt-2 text-xs text-tx-muted">
                  {label}
                  {required && <span className="ml-0.5 text-danger">*</span>}
                </label>
                <div className="flex-1">
                  <input
                    type={type}
                    value={newSupplierForm[key]}
                    onChange={(e) =>
                      setNewSupplierForm((f) => ({ ...f, [key]: e.target.value }))
                    }
                    aria-invalid={Boolean(erroresProveedor[key])}
                    className={`w-full rounded-lg border px-3 py-1.5 text-sm focus:outline-none focus:ring-2 ${
                      erroresProveedor[key]
                        ? 'border-danger focus:ring-red-400'
                        : 'border-input-border focus:ring-secondary'
                    }`}
                    placeholder={required ? 'Obligatorio' : 'Opcional'}
                  />
                  {erroresProveedor[key] && (
                    <p className="mt-1 text-xs text-danger">{erroresProveedor[key]}</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <ErrorBanner message={error} className="mb-4" onDismiss={() => setError('')} />

      {problemas.length > 0 && !error && (
        <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2">
          <p className="mb-1 text-xs font-medium text-amber-800">
            Falta completar {problemas.length} punto(s) antes de confirmar:
          </p>
          <ul className="list-inside list-disc space-y-0.5 text-xs text-amber-700">
            {problemas.slice(0, 5).map((p) => (
              <li key={p}>{p}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="space-y-3">
        {items.map((state, idx) => {
          const original = processed.items[idx]
          const producto = productoDe(state)
          const permiteDecimales = state.use_new
            ? state.new_product.allow_decimal_stock
            : Boolean(producto?.allow_decimal_stock)

          return (
            <div
              key={state.invoice_item_id}
              className={`rounded-xl border bg-surface p-4 ${
                original.confidence !== 'high' ? 'border-yellow-300' : 'border-brand-border'
              }`}
            >
              <div className="mb-3 flex items-start justify-between gap-4">
                <p className="text-xs text-tx-muted">
                  Línea {idx + 1} · leído por la IA: «{original.description}» ·{' '}
                  {parseFloat(original.quantity)} × $
                  {parseFloat(original.unit_price).toFixed(2)}
                </p>
                <div className="flex shrink-0 items-center gap-2">
                  <Badge value={original.confidence} />
                  <label className="flex items-center gap-1 text-xs text-tx-muted">
                    <input
                      type="checkbox"
                      checked={state.skip}
                      onChange={(e) => setItem(idx, { skip: e.target.checked })}
                    />
                    Omitir
                  </label>
                </div>
              </div>

              {!state.skip && (
                <div className="space-y-3">
                  {/* Corrección de los datos extraídos */}
                  <div className="grid grid-cols-1 gap-2 sm:grid-cols-4">
                    <div className="sm:col-span-2">
                      <label className="mb-0.5 block text-xs text-tx-muted">Descripción</label>
                      <input
                        type="text"
                        value={state.description}
                        onChange={(e) => setItem(idx, { description: e.target.value })}
                        className="w-full rounded border border-input-border px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-secondary"
                      />
                    </div>
                    <div>
                      <label className="mb-0.5 block text-xs text-tx-muted">Cantidad</label>
                      <input
                        type="number"
                        step={permiteDecimales ? '0.001' : '1'}
                        min="0"
                        value={state.quantity}
                        onChange={(e) => setItem(idx, { quantity: e.target.value })}
                        className="w-full rounded border border-input-border px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-secondary"
                      />
                    </div>
                    <div>
                      <label className="mb-0.5 block text-xs text-tx-muted">Precio unit.</label>
                      <input
                        type="number"
                        step="0.01"
                        min="0"
                        value={state.unit_price}
                        onChange={(e) => setItem(idx, { unit_price: e.target.value })}
                        className="w-full rounded border border-input-border px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-secondary"
                      />
                    </div>
                  </div>

                  {/* Producto asociado */}
                  <div className="flex items-center gap-2">
                    <label className="w-28 shrink-0 text-xs text-tx-muted">
                      Asociar a producto
                    </label>
                    {!state.use_new ? (
                      <select
                        value={state.product_id}
                        onChange={(e) => {
                          const pid = e.target.value
                          const autoSku = pid
                            ? processed.supplier_product_skus?.[parseInt(pid, 10)] ?? ''
                            : ''
                          setItem(idx, { product_id: pid, supplier_sku: autoSku })
                        }}
                        className={`flex-1 rounded-lg border px-3 py-1.5 text-sm focus:outline-none focus:ring-2 ${
                          state.product_id
                            ? 'border-input-border focus:ring-secondary'
                            : 'border-amber-400 focus:ring-amber-300'
                        }`}
                      >
                        <option value="">Elegí un producto…</option>
                        {products.map((p) => (
                          <option key={p.id} value={p.id}>
                            {p.name} ({p.sku})
                          </option>
                        ))}
                      </select>
                    ) : (
                      <span className="text-xs italic text-tx-muted">
                        Se creará el producto detallado abajo
                      </span>
                    )}
                    <button
                      type="button"
                      onClick={() => setItem(idx, { use_new: !state.use_new, product_id: '' })}
                      className="whitespace-nowrap text-xs text-primary-text hover:underline"
                    >
                      {state.use_new ? '← Usar existente' : '+ Producto nuevo'}
                    </button>
                  </div>

                  {/* Producto nuevo */}
                  {state.use_new && (
                    <div className="grid grid-cols-1 gap-2 rounded-lg bg-sidebar p-3 sm:grid-cols-2">
                      {[
                        { key: 'sku', label: 'SKU', required: true },
                        { key: 'name', label: 'Nombre', required: true },
                        { key: 'description', label: 'Descripción' },
                        { key: 'price', label: 'Precio', type: 'number' },
                        { key: 'minimum_stock', label: 'Stock mínimo', type: 'number' },
                      ].map(({ key, label, required, type = 'text' }) => (
                        <div key={key}>
                          <label className="mb-0.5 block text-xs text-tx-muted">
                            {label}
                            {required && <span className="ml-0.5 text-danger">*</span>}
                          </label>
                          <input
                            type={type}
                            step={type === 'number' ? '0.01' : undefined}
                            value={state.new_product[key]}
                            onChange={(e) =>
                              setItem(idx, {
                                new_product: { ...state.new_product, [key]: e.target.value },
                              })
                            }
                            className="w-full rounded border border-input-border px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-secondary"
                          />
                        </div>
                      ))}
                      <label className="flex items-center gap-2 text-xs text-tx-secondary sm:col-span-2">
                        <input
                          type="checkbox"
                          checked={state.new_product.allow_decimal_stock}
                          onChange={(e) =>
                            setItem(idx, {
                              new_product: {
                                ...state.new_product,
                                allow_decimal_stock: e.target.checked,
                              },
                            })
                          }
                        />
                        Se vende a granel (admite cantidades con decimales)
                      </label>
                    </div>
                  )}

                  {/* SKU del proveedor */}
                  <div className="flex items-center gap-2">
                    <label className="w-28 shrink-0 text-xs text-tx-muted">SKU del proveedor</label>
                    <input
                      type="text"
                      placeholder="Opcional — sirve para auto-completar próximas facturas"
                      value={state.supplier_sku}
                      onChange={(e) => setItem(idx, { supplier_sku: e.target.value })}
                      className="flex-1 rounded-lg border border-input-border px-3 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-secondary"
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

// ── Página principal ──────────────────────────────────────────────────────────
export default function Invoices() {
  const [invoices, setInvoices] = useState([])
  const [loading, setLoading] = useState(true)
  const [products, setProducts] = useState([])
  const [suppliers, setSuppliers] = useState([])
  const [step, setStep] = useState('list') // 'list' | 'upload' | 'review'
  const [processed, setProcessed] = useState(null)
  const [detailModal, setDetailModal] = useState(null)
  const [error, setError] = useState('')

  async function load() {
    setLoading(true)
    try {
      const { data } = await client.get('/invoices')
      setInvoices(data)
      setError('')
    } catch (err) {
      setError(getErrorMessage(err, 'No pudimos cargar las facturas.'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    client.get('/products').then((r) => setProducts(r.data)).catch(() => {})
    client.get('/suppliers').then((r) => setSuppliers(r.data)).catch(() => {})
  }, [])

  function handleProcessed(data) {
    setProcessed(data)
    setStep('review')
  }

  function volverAlListado() {
    setStep('list')
    setProcessed(null)
    load()
  }

  function resumeReview(inv) {
    // Se reconstruye un objeto equivalente al del procesamiento a partir de la
    // factura guardada, para poder retomar una revisión pendiente.
    setProcessed({
      invoice_id: inv.id,
      supplier: inv.supplier_name ?? null,
      supplier_id: inv.supplier_id ?? null,
      date: inv.date ?? null,
      items: (inv.items ?? []).map((item) => ({
        id: item.id,
        description: item.description,
        quantity: item.quantity,
        unit_price: item.unit_price,
        confidence: item.confidence,
        suggested_product_id: null,
        suggested_product_name: null,
      })),
      supplier_product_skus: {},
    })
    setStep('review')
  }

  if (step === 'review' && processed) {
    return (
      <div>
        <div className="mb-6 flex items-center gap-3">
          <button
            onClick={volverAlListado}
            className="text-xl font-bold text-tx-primary hover:underline"
          >
            Facturas
          </button>
          <span className="text-tx-muted">›</span>
          <span className="text-sm text-tx-muted">Revisión</span>
        </div>
        <ReviewStep
          processed={processed}
          products={products}
          suppliers={suppliers}
          onConfirmed={volverAlListado}
          onCancel={volverAlListado}
          onBack={volverAlListado}
        />
      </div>
    )
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-bold text-tx-primary">Facturas</h1>
        <button
          onClick={() => setStep(step === 'upload' ? 'list' : 'upload')}
          className="rounded-lg bg-secondary px-4 py-2 text-sm font-medium text-secondary-text transition hover:bg-secondary-dark"
        >
          {step === 'upload' ? 'Cerrar' : '+ Subir factura'}
        </button>
      </div>

      <ErrorBanner message={error} className="mb-4" onDismiss={() => setError('')} />

      {step === 'upload' && (
        <div className="mb-8 rounded-xl border border-brand-border bg-surface p-6 shadow">
          <UploadStep onProcessed={handleProcessed} onCancel={() => setStep('list')} />
        </div>
      )}

      {loading ? (
        <p className="text-sm text-tx-muted">Cargando…</p>
      ) : (
        <div className="overflow-hidden rounded-xl border border-brand-border bg-surface shadow">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[520px] text-sm">
              <thead className="border-b border-brand-border bg-sidebar text-xs uppercase tracking-wide text-tx-muted">
                <tr>
                  {['N.º', 'Fecha', 'Proveedor', 'Estado', 'Líneas', ''].map((h) => (
                    <th key={h} className="px-4 py-3 text-left font-medium">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {invoices.map((inv) => (
                  <tr key={inv.id}>
                    <td className="px-4 py-3 text-xs text-tx-muted">{inv.id}</td>
                    <td className="px-4 py-3 text-tx-secondary">{inv.date ?? '—'}</td>
                    <td className="px-4 py-3 font-medium text-tx-primary">
                      {inv.supplier_name ?? '—'}
                    </td>
                    <td className="px-4 py-3">
                      <Badge value={inv.status} />
                    </td>
                    <td className="px-4 py-3 text-tx-muted">{inv.items?.length ?? 0}</td>
                    <td className="space-x-3 px-4 py-3 text-right">
                      {inv.status === 'pending' && (
                        <button
                          onClick={() => resumeReview(inv)}
                          className="text-xs font-medium text-warning hover:underline"
                        >
                          Revisar
                        </button>
                      )}
                      <button
                        onClick={() => setDetailModal(inv)}
                        className="text-xs text-primary-text hover:underline"
                      >
                        Detalle
                      </button>
                    </td>
                  </tr>
                ))}
                {invoices.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-4 py-6 text-center text-tx-muted">
                      Todavía no hay facturas.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {detailModal && (
        <Modal title={`Factura n.º ${detailModal.id}`} onClose={() => setDetailModal(null)}>
          <div className="space-y-3 text-sm">
            <div className="flex flex-wrap gap-4 text-sm">
              <span>
                <span className="text-tx-muted">Proveedor:</span>{' '}
                {detailModal.supplier_name ?? '—'}
              </span>
              <span>
                <span className="text-tx-muted">Fecha:</span> {detailModal.date ?? '—'}
              </span>
              <span>
                <span className="text-tx-muted">Estado:</span>{' '}
                <Badge value={detailModal.status} />
              </span>
            </div>
            {detailModal.items?.length > 0 && (
              <div className="overflow-x-auto rounded-lg border border-brand-border">
                <table className="w-full text-xs">
                  <thead className="bg-sidebar text-tx-muted">
                    <tr>
                      {[
                        'Descripción',
                        'Cant.',
                        'Precio unit.',
                        'Confianza',
                        'SKU proveedor',
                        'Estado',
                      ].map((h) => (
                        <th key={h} className="px-3 py-2 text-left">
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {detailModal.items.map((item) => (
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
                          {item.skipped ? '—' : `$${parseFloat(item.unit_price).toFixed(2)}`}
                        </td>
                        <td className="px-3 py-2">
                          {item.skipped ? '—' : <Badge value={item.confidence} />}
                        </td>
                        <td className="px-3 py-2 font-mono text-tx-muted">
                          {item.skipped ? '—' : item.supplier_sku ?? '—'}
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
              </div>
            )}
          </div>
        </Modal>
      )}
    </div>
  )
}
