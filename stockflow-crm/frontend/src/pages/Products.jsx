import { useEffect, useState } from 'react'
import client from '../api/client'
import { getErrorMessage, getFieldErrors } from '../api/errors'
import ActionButton from '../components/ui/ActionButton'
import ErrorBanner from '../components/ui/ErrorBanner'
import FormField from '../components/ui/FormField'
import Modal from '../components/ui/Modal'
import {
  cantidadStock,
  numeroNoNegativo,
  requerido,
  sku as validarSku,
  validarFormulario,
} from '../utils/validation'

const VACIO = {
  sku: '',
  name: '',
  description: '',
  price: '',
  current_stock: '',
  minimum_stock: '',
  allow_decimal_stock: false,
}

// El nombre de un producto sí admite números ("Coca Cola 500ml"), a diferencia
// del nombre de una persona.
const REGLAS = {
  sku: validarSku,
  name: requerido,
  price: numeroNoNegativo,
  current_stock: (valor, valores) => cantidadStock(valor, valores.allow_decimal_stock),
  minimum_stock: (valor, valores) => cantidadStock(valor, valores.allow_decimal_stock),
}

function formatearNumero(valor) {
  const numero = parseFloat(valor)
  return Number.isInteger(numero) ? String(numero) : String(numero)
}

export default function Products() {
  const [products, setProducts] = useState([])
  const [modal, setModal] = useState(null) // null | 'create' | producto
  const [form, setForm] = useState(VACIO)
  const [errores, setErrores] = useState({})
  const [error, setError] = useState('')
  const [errorGeneral, setErrorGeneral] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  async function load() {
    setLoading(true)
    try {
      const { data } = await client.get('/products')
      setProducts(data)
      setErrorGeneral('')
    } catch (err) {
      setErrorGeneral(getErrorMessage(err, 'No pudimos cargar los productos.'))
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

  function openEdit(p) {
    setForm({
      sku: p.sku,
      name: p.name,
      description: p.description ?? '',
      price: p.price,
      current_stock: p.current_stock,
      minimum_stock: p.minimum_stock,
      allow_decimal_stock: p.allow_decimal_stock ?? false,
    })
    setErrores({})
    setError('')
    setModal(p)
  }

  function actualizar(campo, valor) {
    setForm((f) => {
      const siguiente = { ...f, [campo]: valor }
      // Al cambiar el flag hay que revalidar las cantidades ya cargadas.
      if (campo === 'allow_decimal_stock') {
        setErrores((e) => ({
          ...e,
          current_stock: REGLAS.current_stock(siguiente.current_stock, siguiente),
          minimum_stock: REGLAS.minimum_stock(siguiente.minimum_stock, siguiente),
        }))
      } else if (REGLAS[campo] && errores[campo]) {
        setErrores((e) => ({ ...e, [campo]: REGLAS[campo](valor, siguiente) }))
      }
      return siguiente
    })
  }

  function validarCampo(campo) {
    if (!REGLAS[campo]) return
    setErrores((e) => ({ ...e, [campo]: REGLAS[campo](form[campo], form) }))
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
    const body = {
      ...form,
      description: form.description.trim() || null,
      price: parseFloat(form.price),
      current_stock: parseFloat(form.current_stock),
      minimum_stock: parseFloat(form.minimum_stock),
    }
    try {
      if (modal === 'create') {
        await client.post('/products', body)
      } else {
        await client.put(`/products/${modal.id}`, body)
      }
      setModal(null)
      load()
    } catch (err) {
      // El modal permanece abierto: cerrar y perder lo cargado era justamente
      // lo que hacía que un error pareciera que "no pasó nada".
      setError(getErrorMessage(err, 'No pudimos guardar el producto.'))
      setErrores((previos) => ({ ...previos, ...getFieldErrors(err) }))
    } finally {
      setSaving(false)
    }
  }

  async function handleToggleActive(p) {
    try {
      await client.put(`/products/${p.id}`, { is_active: !p.is_active })
      load()
    } catch (err) {
      setErrorGeneral(getErrorMessage(err, 'No pudimos actualizar el producto.'))
    }
  }

  async function handleDelete(p) {
    if (!confirm(`¿Eliminar el producto «${p.name}»?`)) return
    try {
      await client.delete(`/products/${p.id}`)
      setErrorGeneral('')
      load()
    } catch (err) {
      setErrorGeneral(getErrorMessage(err, 'No pudimos eliminar el producto.'))
    }
  }

  const decimalesActivos = Boolean(form.allow_decimal_stock)
  const pasoCantidad = decimalesActivos ? '0.001' : '1'

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-bold text-tx-primary">Productos</h1>
        <button
          onClick={openCreate}
          className="rounded-lg bg-secondary px-4 py-2 text-sm font-medium text-secondary-text transition hover:bg-secondary-dark"
        >
          + Nuevo producto
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
            <table className="w-full min-w-[560px] text-sm">
              <thead className="border-b border-brand-border bg-sidebar text-xs uppercase tracking-wide text-tx-muted">
                <tr>
                  {['SKU', 'Nombre', 'Precio', 'Stock', 'Stock mínimo', ''].map((h) => (
                    <th key={h} className="px-4 py-3 text-left font-medium">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {products.map((p) => (
                  <tr
                    key={p.id}
                    className={
                      !p.is_active ? 'bg-gray-50 opacity-50' : p.low_stock ? 'bg-red-50' : ''
                    }
                  >
                    <td className="px-4 py-3 font-mono text-xs text-tx-secondary">{p.sku}</td>
                    <td className="px-4 py-3 font-medium text-tx-primary">
                      {p.name}
                      {p.low_stock && p.is_active && (
                        <span className="ml-2 text-xs font-normal text-danger">stock bajo</span>
                      )}
                      {!p.is_active && (
                        <span className="ml-2 text-xs font-normal text-tx-muted">inactivo</span>
                      )}
                      {p.allow_decimal_stock && (
                        <span className="ml-2 text-xs font-normal text-tx-muted">a granel</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-tx-secondary">
                      ${parseFloat(p.price).toFixed(2)}
                    </td>
                    <td className="px-4 py-3 text-tx-secondary">
                      {formatearNumero(p.current_stock)}
                    </td>
                    <td className="px-4 py-3 text-tx-secondary">
                      {formatearNumero(p.minimum_stock)}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex flex-wrap justify-end gap-2">
                        <ActionButton tono="editar" onClick={() => openEdit(p)}>
                          Editar
                        </ActionButton>
                        <ActionButton
                          tono={p.is_active ? 'desactivar' : 'activar'}
                          onClick={() => handleToggleActive(p)}
                        >
                          {p.is_active ? 'Desactivar' : 'Activar'}
                        </ActionButton>
                        {/* El backend informa si el producto se puede borrar, así
                            que el botón se deshabilita con el motivo a la vista
                            en lugar de fallar recién al pulsarlo. */}
                        <ActionButton
                          tono="eliminar"
                          onClick={() => handleDelete(p)}
                          disabled={p.can_delete === false}
                          title={p.delete_blocked_reason ?? 'Eliminar el producto'}
                        >
                          Eliminar
                        </ActionButton>
                      </div>
                    </td>
                  </tr>
                ))}
                {products.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-4 py-6 text-center text-tx-muted">
                      Todavía no hay productos.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {modal && (
        <Modal
          title={modal === 'create' ? 'Nuevo producto' : 'Editar producto'}
          onClose={() => setModal(null)}
          disabled={saving}
        >
          <form onSubmit={handleSave} noValidate className="space-y-3">
            <ErrorBanner message={error} />

            <FormField
              name="sku"
              label="SKU"
              required
              disabled={modal !== 'create' || saving}
              value={form.sku}
              error={errores.sku}
              hint={modal !== 'create' ? 'El SKU no se puede modificar.' : undefined}
              onChange={(e) => actualizar('sku', e.target.value)}
              onBlur={() => validarCampo('sku')}
            />
            <FormField
              name="name"
              label="Nombre"
              required
              disabled={saving}
              value={form.name}
              error={errores.name}
              onChange={(e) => actualizar('name', e.target.value)}
              onBlur={() => validarCampo('name')}
            />
            <FormField
              name="description"
              label="Descripción"
              disabled={saving}
              value={form.description}
              hint="Opcional."
              onChange={(e) => actualizar('description', e.target.value)}
            />
            <FormField
              name="price"
              label="Precio"
              type="number"
              step="0.01"
              min="0"
              required
              disabled={saving}
              value={form.price}
              error={errores.price}
              onChange={(e) => actualizar('price', e.target.value)}
              onBlur={() => validarCampo('price')}
            />

            <FormField name="allow_decimal_stock" label="Unidad de medida">
              <label className="flex items-start gap-2 rounded-lg border border-input-border px-3 py-2 text-sm">
                <input
                  id="campo-allow_decimal_stock"
                  type="checkbox"
                  className="mt-0.5"
                  disabled={saving}
                  checked={decimalesActivos}
                  onChange={(e) => actualizar('allow_decimal_stock', e.target.checked)}
                />
                <span className="text-tx-secondary">
                  Admite stock decimal
                  <span className="block text-xs text-tx-muted">
                    Activalo solo para productos a granel (kilos, litros, metros).
                    Los productos por unidad no pueden tener existencias como 3,5.
                  </span>
                </span>
              </label>
            </FormField>

            <FormField
              name="current_stock"
              label="Stock actual"
              type="number"
              step={pasoCantidad}
              min="0"
              required
              disabled={saving}
              value={form.current_stock}
              error={errores.current_stock}
              onChange={(e) => actualizar('current_stock', e.target.value)}
              onBlur={() => validarCampo('current_stock')}
            />
            <FormField
              name="minimum_stock"
              label="Stock mínimo"
              type="number"
              step={pasoCantidad}
              min="0"
              required
              disabled={saving}
              value={form.minimum_stock}
              error={errores.minimum_stock}
              onChange={(e) => actualizar('minimum_stock', e.target.value)}
              onBlur={() => validarCampo('minimum_stock')}
            />

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
    </div>
  )
}
