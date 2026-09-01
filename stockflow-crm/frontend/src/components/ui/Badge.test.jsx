import { render, screen } from '@testing-library/react'
import Badge from './Badge'

describe('Badge', () => {
  it('traduce los estados de pedido al español', () => {
    render(<Badge value="pending" />)
    expect(screen.getByText('pendiente')).toBeInTheDocument()
  })

  it('traduce "exit" como "venta"', () => {
    render(<Badge value="exit" />)
    expect(screen.getByText('venta')).toBeInTheDocument()
  })

  it('aplica clases verdes al estado entregado', () => {
    render(<Badge value="delivered" />)
    expect(screen.getByText('entregado')).toHaveClass('bg-green-100', 'text-green-800')
  })

  it('aplica clases amarillas al estado pendiente', () => {
    render(<Badge value="pending" />)
    expect(screen.getByText('pendiente')).toHaveClass('bg-yellow-100', 'text-yellow-800')
  })

  it('aplica clases rojas al estado rechazado', () => {
    render(<Badge value="rejected" />)
    expect(screen.getByText('rechazada')).toHaveClass('bg-red-100', 'text-red-800')
  })

  it('aplica clases rojas al movimiento de venta', () => {
    render(<Badge value="exit" />)
    expect(screen.getByText('venta')).toHaveClass('bg-red-100', 'text-red-800')
  })

  it('aplica clases verdes al movimiento de entrada', () => {
    render(<Badge value="entry" />)
    expect(screen.getByText('entrada')).toHaveClass('bg-green-100', 'text-green-800')
  })

  it('aplica clases grises al movimiento de ajuste', () => {
    render(<Badge value="adjustment" />)
    expect(screen.getByText('ajuste')).toHaveClass('bg-gray-100', 'text-gray-700')
  })

  it('usa gris y muestra el valor crudo si no lo conoce', () => {
    render(<Badge value="estado-desconocido" />)
    expect(screen.getByText('estado-desconocido')).toHaveClass(
      'bg-gray-100',
      'text-gray-700'
    )
  })

  it('se renderiza como un span', () => {
    render(<Badge value="confirmed" />)
    expect(screen.getByText('confirmada').tagName).toBe('SPAN')
  })
})
