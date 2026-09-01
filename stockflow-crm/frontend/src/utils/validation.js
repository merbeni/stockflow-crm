/**
 * Validaciones de formulario del lado del cliente.
 *
 * Replican las reglas del backend para dar aviso inmediato, sin reemplazarlas:
 * el servidor sigue siendo la autoridad. Todas devuelven un mensaje de error o
 * `null` si el valor es válido.
 */

const RE_EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/
const RE_TELEFONO = /^[0-9+\-\s().]{6,}$/
const RE_SKU = /^[A-Za-z0-9._\-/]+$/

export function requerido(valor) {
  if (valor === null || valor === undefined) return 'Este campo es obligatorio.'
  if (typeof valor === 'string' && !valor.trim()) return 'Este campo es obligatorio.'
  return null
}

export function email(valor) {
  const falta = requerido(valor)
  if (falta) return falta
  return RE_EMAIL.test(valor.trim()) ? null : 'No es una dirección de correo válida.'
}

export function telefono(valor) {
  const falta = requerido(valor)
  if (falta) return falta
  const texto = valor.trim()
  const digitos = (texto.match(/\d/g) || []).length
  if (!RE_TELEFONO.test(texto) || digitos < 6) {
    return 'Debe incluir al menos 6 dígitos y solo los signos + - ( ) .'
  }
  return null
}

/** Nombre de una persona: no admite números. */
export function nombrePersona(valor) {
  const falta = requerido(valor)
  if (falta) return falta
  const texto = valor.trim()
  if (texto.length < 2) return 'Debe tener al menos 2 caracteres.'
  if (/\d/.test(texto)) return 'No puede contener números.'
  return null
}

export function sku(valor) {
  const falta = requerido(valor)
  if (falta) return falta
  return RE_SKU.test(valor.trim())
    ? null
    : 'Solo letras, números y los signos . _ - / (sin espacios).'
}

export function password(valor) {
  if (!valor) return 'Este campo es obligatorio.'
  if (valor.length < 8) return 'Debe tener al menos 8 caracteres.'
  if (!/[a-zA-Z]/.test(valor)) return 'Debe incluir al menos una letra.'
  if (!/\d/.test(valor)) return 'Debe incluir al menos un número.'
  return null
}

export function numeroNoNegativo(valor) {
  const falta = requerido(valor)
  if (falta) return falta
  const numero = Number(valor)
  if (Number.isNaN(numero)) return 'Debe ser un número válido.'
  if (numero < 0) return 'No puede ser negativo.'
  return null
}

/** Cantidad de stock: entera salvo que el producto se venda a granel. */
export function cantidadStock(valor, permiteDecimales) {
  const invalido = numeroNoNegativo(valor)
  if (invalido) return invalido
  if (!permiteDecimales && !Number.isInteger(Number(valor))) {
    return 'Debe ser un número entero. Marcá "Admite stock decimal" si se vende a granel.'
  }
  return null
}

/**
 * Valida un formulario completo.
 *
 * @param {object} valores  Valores del formulario.
 * @param {object} reglas   Mapa `{ campo: (valor, valores) => mensaje|null }`.
 * @returns {Record<string,string>} Solo los campos con error.
 */
export function validarFormulario(valores, reglas) {
  const errores = {}
  for (const [campo, regla] of Object.entries(reglas)) {
    const mensaje = regla(valores[campo], valores)
    if (mensaje) errores[campo] = mensaje
  }
  return errores
}
