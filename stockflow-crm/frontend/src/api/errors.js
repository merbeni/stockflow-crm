/**
 * Normalización de errores de la API.
 *
 * Motivo: FastAPI devuelve en los errores 422 un `detail` que es una **lista de
 * objetos**, no un string. Las páginas hacían `setError(err.response.data.detail)`
 * y luego renderizaban `{error}` en el JSX, así que React lanzaba
 * "Objects are not valid as a React child", desmontaba el árbol y dejaba la
 * pantalla en blanco.
 *
 * Estas funciones garantizan devolver **siempre** strings, sea cual sea la forma
 * de la respuesta.
 */

const MENSAJE_GENERICO = 'Ocurrió un error inesperado. Por favor intentá nuevamente.'
const MENSAJE_SIN_RED = 'No se pudo conectar con el servidor. Verificá tu conexión e intentá de nuevo.'

const MENSAJES_POR_ESTADO = {
  400: 'La solicitud no es válida.',
  401: 'Tu sesión expiró. Iniciá sesión nuevamente.',
  403: 'No tenés permisos para realizar esta acción.',
  404: 'No encontramos lo que buscabas.',
  409: 'La operación entra en conflicto con datos existentes.',
  413: 'El archivo es demasiado grande.',
  415: 'El tipo de archivo no está permitido.',
  422: 'Revisá los datos ingresados.',
  429: 'Demasiados intentos. Esperá un momento antes de reintentar.',
  500: MENSAJE_GENERICO,
  502: 'El servicio no está disponible en este momento.',
  503: 'El servicio no está disponible en este momento.',
}

/** Convierte a texto un elemento cualquiera de un `detail` con forma de lista. */
function itemATexto(item) {
  if (typeof item === 'string') return item
  if (!item || typeof item !== 'object') return ''

  // Forma estándar de un error de validación de FastAPI/Pydantic.
  if (typeof item.msg === 'string') {
    const campo = Array.isArray(item.loc)
      ? item.loc.filter((p) => p !== 'body' && p !== 'query' && p !== 'path').join('.')
      : ''
    return campo ? `${campo}: ${item.msg}` : item.msg
  }
  if (typeof item.detail === 'string') return item.detail
  return ''
}

/**
 * Devuelve un mensaje de error legible. Siempre un string, nunca un objeto.
 *
 * @param {unknown} err            Error capturado (normalmente de axios).
 * @param {string}  [respaldo]     Mensaje a usar si no se puede extraer otro.
 * @returns {string}
 */
export function getErrorMessage(err, respaldo = MENSAJE_GENERICO) {
  if (!err) return respaldo

  // Sin respuesta del servidor: problema de red, CORS o backend caído.
  if (err.request && !err.response) return MENSAJE_SIN_RED

  const data = err.response?.data
  const status = err.response?.status

  if (typeof data === 'string' && data.trim()) return data.trim()

  const detail = data?.detail

  if (typeof detail === 'string' && detail.trim()) return detail.trim()

  if (Array.isArray(detail)) {
    const textos = detail.map(itemATexto).filter(Boolean)
    if (textos.length) return textos.join(' · ')
  }

  if (detail && typeof detail === 'object') {
    const texto = itemATexto(detail)
    if (texto) return texto
  }

  // Algunos handlers devuelven { message: "..." }.
  if (typeof data?.message === 'string' && data.message.trim()) return data.message.trim()

  if (status && MENSAJES_POR_ESTADO[status]) return MENSAJES_POR_ESTADO[status]

  if (typeof err.message === 'string' && err.message.trim()) return err.message.trim()

  return respaldo
}

/**
 * Devuelve un mapa `{ campo: mensaje }` para pintar el error debajo de cada input.
 * Todos los valores son strings. Si no hay errores por campo, devuelve `{}`.
 *
 * @param {unknown} err
 * @returns {Record<string, string>}
 */
export function getFieldErrors(err) {
  const data = err?.response?.data
  const resultado = {}

  // Formato nuevo del backend: { detail: "...", errors: { campo: "mensaje" } }
  if (data?.errors && typeof data.errors === 'object' && !Array.isArray(data.errors)) {
    for (const [campo, mensaje] of Object.entries(data.errors)) {
      if (typeof mensaje === 'string') resultado[campo] = mensaje
    }
    return resultado
  }

  // Retrocompatibilidad con el formato crudo de FastAPI.
  if (Array.isArray(data?.detail)) {
    for (const item of data.detail) {
      if (!item || typeof item !== 'object' || !Array.isArray(item.loc)) continue
      const campo = item.loc
        .filter((p) => p !== 'body' && p !== 'query' && p !== 'path')
        .join('.')
      if (campo && typeof item.msg === 'string' && !resultado[campo]) {
        resultado[campo] = item.msg
      }
    }
  }

  return resultado
}
