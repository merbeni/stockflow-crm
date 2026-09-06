import { describe, it, expect } from 'vitest'
import { problemaDelArchivo } from './Invoices'

/**
 * El backend valida igual, pero recién después de recibir el archivo entero.
 * Con una factura escaneada pesada eso es una espera larga para un error que
 * se podía ver de entrada, así que la comprobación se adelanta al navegador.
 */
const archivo = (tipo, bytes) => ({ type: tipo, size: bytes })

describe('problemaDelArchivo', () => {
  it('acepta los cuatro formatos que el backend admite', () => {
    for (const tipo of ['application/pdf', 'image/jpeg', 'image/png', 'image/webp']) {
      expect(problemaDelArchivo(archivo(tipo, 1024))).toBeNull()
    }
  })

  it('rechaza un formato que no es factura', () => {
    const mensaje = problemaDelArchivo(archivo('application/x-msdownload', 1024))
    expect(mensaje).toMatch(/PDF, JPG, PNG o WEBP/)
  })

  it('rechaza un archivo que supera los 20 MB', () => {
    const mensaje = problemaDelArchivo(archivo('application/pdf', 21 * 1024 * 1024))
    expect(mensaje).toMatch(/20 MB/)
    // El peso real tiene que aparecer: "es muy grande" no dice cuánto recortar.
    expect(mensaje).toMatch(/21\.0 MB/)
  })

  it('acepta exactamente 20 MB', () => {
    // Límite justo: el backend rechaza con "mayor que", no con "mayor o igual".
    expect(problemaDelArchivo(archivo('application/pdf', 20 * 1024 * 1024))).toBeNull()
  })

  it('comprueba el formato antes que el tamaño', () => {
    // Un .exe enorme tiene los dos problemas; el que importa es el formato.
    const mensaje = problemaDelArchivo(archivo('text/csv', 50 * 1024 * 1024))
    expect(mensaje).toMatch(/formato/)
  })
})
