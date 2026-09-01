import { render, screen } from '@testing-library/react'
import { vi } from 'vitest'
import ErrorBoundary from './ErrorBoundary'

function Explota() {
  throw new Error('fallo de render')
}

describe('ErrorBoundary', () => {
  beforeEach(() => {
    // React registra el error en consola; se silencia para no ensuciar la salida.
    vi.spyOn(console, 'error').mockImplementation(() => {})
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('muestra el contenido cuando no hay errores', () => {
    render(
      <ErrorBoundary>
        <p>contenido normal</p>
      </ErrorBoundary>
    )
    expect(screen.getByText('contenido normal')).toBeInTheDocument()
  })

  it('muestra una pantalla de recuperación en lugar de quedar en blanco', () => {
    render(
      <ErrorBoundary>
        <Explota />
      </ErrorBoundary>
    )
    expect(screen.getByText('Algo salió mal')).toBeInTheDocument()
    expect(screen.getByText('Reintentar')).toBeInTheDocument()
  })
})
