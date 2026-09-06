import { describe, it, expect } from 'vitest'
import { soloLoCambiado } from './formulario'

describe('soloLoCambiado', () => {
  const original = {
    sku: 'DEC-1',
    name: 'Duplicado',
    description: '',
    price: '10.00',
    current_stock: '3.000',
  }

  it('manda solo el campo que se editó', () => {
    const enviado = soloLoCambiado({ ...original, price: 999.99 }, original)
    expect(enviado).toEqual({ price: 999.99 })
  })

  it('no manda nada si no se tocó nada', () => {
    expect(soloLoCambiado({ ...original }, original)).toEqual({})
  })

  it('trata «10.00» y 10 como el mismo valor', () => {
    // El servidor devuelve los importes con dos decimales y el formulario los
    // arma como número: sin esto, abrir y guardar sin editar reenviaba el
    // precio y podía pisar el de otra persona.
    const enviado = soloLoCambiado({ ...original, price: 10, current_stock: 3 }, original)
    expect(enviado).toEqual({})
  })

  it('trata null y la cadena vacía como lo mismo en los campos opcionales', () => {
    const enviado = soloLoCambiado({ ...original, description: null }, original)
    expect(enviado).toEqual({})
  })

  it('sí manda un campo opcional cuando se lo completa', () => {
    const enviado = soloLoCambiado({ ...original, description: 'Nueva nota' }, original)
    expect(enviado).toEqual({ description: 'Nueva nota' })
  })

  it('distingue false de cadena vacía en los campos de sí/no', () => {
    const base = { allow_decimal_stock: true }
    expect(soloLoCambiado({ allow_decimal_stock: false }, base)).toEqual({
      allow_decimal_stock: false,
    })
  })

  it('en un alta, sin original, manda todo', () => {
    expect(soloLoCambiado(original, null)).toEqual(original)
  })
})
