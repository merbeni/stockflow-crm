/**
 * Tests de la normalización de errores.
 *
 * Cubren la causa raíz de la pantalla en blanco: FastAPI devuelve en los 422 un
 * `detail` que es una lista de objetos, y renderizarlo directamente hacía que
 * React lanzara "Objects are not valid as a React child".
 */
import { describe, it, expect } from 'vitest'
import { getErrorMessage, getFieldErrors } from './errors'

const error422Crudo = {
  response: {
    status: 422,
    data: {
      detail: [
        {
          type: 'value_error',
          loc: ['body', 'email'],
          msg: 'value is not a valid email address',
        },
        {
          type: 'string_too_long',
          loc: ['body', 'name'],
          msg: 'String should have at most 255 characters',
        },
      ],
    },
  },
}

describe('getErrorMessage', () => {
  it('devuelve un string cuando detail es una lista de objetos', () => {
    const mensaje = getErrorMessage(error422Crudo)
    expect(typeof mensaje).toBe('string')
    expect(mensaje).toContain('email')
    expect(mensaje).toContain('name')
  })

  it('devuelve el detail tal cual cuando ya es un string', () => {
    expect(
      getErrorMessage({ response: { status: 409, data: { detail: 'SKU duplicado' } } })
    ).toBe('SKU duplicado')
  })

  it('no rompe cuando detail es un objeto suelto', () => {
    const mensaje = getErrorMessage({
      response: { status: 500, data: { detail: { algo: 'raro' } } },
    })
    expect(typeof mensaje).toBe('string')
    expect(mensaje.length).toBeGreaterThan(0)
  })

  it('avisa cuando no hay respuesta del servidor', () => {
    expect(getErrorMessage({ request: {} })).toContain('conectar')
  })

  it('usa el mensaje de respaldo ante un error nulo', () => {
    expect(getErrorMessage(null, 'respaldo')).toBe('respaldo')
  })

  it('nunca devuelve algo que no sea un string', () => {
    const entradas = [
      null,
      undefined,
      {},
      { response: {} },
      { response: { data: null } },
      { response: { data: { detail: [] } } },
      { response: { data: { detail: [{ sin: 'msg' }] } } },
      { response: { data: [1, 2, 3] } },
      { response: { status: 404, data: {} } },
    ]
    for (const entrada of entradas) {
      expect(typeof getErrorMessage(entrada)).toBe('string')
    }
  })
})

describe('getFieldErrors', () => {
  it('usa el mapa "errors" del backend cuando está presente', () => {
    const errores = getFieldErrors({
      response: {
        data: {
          detail: 'Correo electrónico: No es una dirección de correo válida.',
          errors: { email: 'No es una dirección de correo válida.' },
        },
      },
    })
    expect(errores).toEqual({ email: 'No es una dirección de correo válida.' })
  })

  it('convierte el formato crudo de FastAPI en errores por campo', () => {
    const errores = getFieldErrors(error422Crudo)
    expect(errores.email).toBe('value is not a valid email address')
    expect(errores.name).toBe('String should have at most 255 characters')
    for (const valor of Object.values(errores)) {
      expect(typeof valor).toBe('string')
    }
  })

  it('devuelve un objeto vacío si no hay errores por campo', () => {
    expect(getFieldErrors({ response: { data: { detail: 'texto' } } })).toEqual({})
    expect(getFieldErrors(null)).toEqual({})
  })
})
