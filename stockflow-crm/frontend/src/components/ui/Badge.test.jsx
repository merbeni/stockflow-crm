import { render, screen } from '@testing-library/react'
import Badge from './Badge'

describe('Badge', () => {
  it('renders the value as text when no label override exists', () => {
    render(<Badge value="pending" />)
    expect(screen.getByText('pending')).toBeInTheDocument()
  })

  it('renders "sale" label for the "exit" value', () => {
    render(<Badge value="exit" />)
    expect(screen.getByText('sale')).toBeInTheDocument()
  })

  it('applies green classes for delivered status', () => {
    render(<Badge value="delivered" />)
    const el = screen.getByText('delivered')
    expect(el).toHaveClass('bg-green-100', 'text-green-800')
  })

  it('applies yellow classes for pending status', () => {
    render(<Badge value="pending" />)
    const el = screen.getByText('pending')
    expect(el).toHaveClass('bg-yellow-100', 'text-yellow-800')
  })

  it('applies red classes for rejected status', () => {
    render(<Badge value="rejected" />)
    const el = screen.getByText('rejected')
    expect(el).toHaveClass('bg-red-100', 'text-red-800')
  })

  it('applies red classes for exit (sale) movement', () => {
    render(<Badge value="exit" />)
    const el = screen.getByText('sale')
    expect(el).toHaveClass('bg-red-100', 'text-red-800')
  })

  it('applies green classes for entry movement', () => {
    render(<Badge value="entry" />)
    const el = screen.getByText('entry')
    expect(el).toHaveClass('bg-green-100', 'text-green-800')
  })

  it('applies gray classes for adjustment movement', () => {
    render(<Badge value="adjustment" />)
    const el = screen.getByText('adjustment')
    expect(el).toHaveClass('bg-gray-100', 'text-gray-700')
  })

  it('falls back to gray classes for unknown value', () => {
    render(<Badge value="unknown-status" />)
    const el = screen.getByText('unknown-status')
    expect(el).toHaveClass('bg-gray-100', 'text-gray-700')
  })

  it('renders as a span element', () => {
    render(<Badge value="confirmed" />)
    expect(screen.getByText('confirmed').tagName).toBe('SPAN')
  })
})
