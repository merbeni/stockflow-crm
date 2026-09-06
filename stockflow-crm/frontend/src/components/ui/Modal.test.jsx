import { render, screen, fireEvent } from '@testing-library/react'
import { useState } from 'react'
import userEvent from '@testing-library/user-event'
import Modal from './Modal'

describe('Modal', () => {
  it('renders the title', () => {
    render(<Modal title="Test Title" onClose={() => {}}><p>content</p></Modal>)
    expect(screen.getByText('Test Title')).toBeInTheDocument()
  })

  it('renders children', () => {
    render(<Modal title="Title" onClose={() => {}}><p>Child Content</p></Modal>)
    expect(screen.getByText('Child Content')).toBeInTheDocument()
  })

  it('calls onClose when the close button is clicked', () => {
    const onClose = vi.fn()
    render(<Modal title="Title" onClose={onClose}><p>body</p></Modal>)
    fireEvent.click(screen.getByRole('button'))
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('disables the close button when disabled prop is true', () => {
    render(<Modal title="Title" onClose={() => {}} disabled><p>body</p></Modal>)
    expect(screen.getByRole('button')).toBeDisabled()
  })

  it('close button is enabled by default', () => {
    render(<Modal title="Title" onClose={() => {}}><p>body</p></Modal>)
    expect(screen.getByRole('button')).not.toBeDisabled()
  })

  it('does not fire onClose when disabled and button is clicked', () => {
    const onClose = vi.fn()
    render(<Modal title="Title" onClose={onClose} disabled><p>body</p></Modal>)
    fireEvent.click(screen.getByRole('button'))
    expect(onClose).not.toHaveBeenCalled()
  })

  // ── Accesibilidad ──────────────────────────────────────────────────────────
  // Sin esto la ventana era un div flotante: no se cerraba con el teclado, no se
  // anunciaba como diálogo y el botón de cerrar no tenía nombre accesible.

  it('se cierra con la tecla Escape', () => {
    const onClose = vi.fn()
    render(<Modal title="Title" onClose={onClose}><p>body</p></Modal>)
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('ignora Escape mientras hay una operación en curso', () => {
    const onClose = vi.fn()
    render(<Modal title="Title" onClose={onClose} disabled><p>body</p></Modal>)
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(onClose).not.toHaveBeenCalled()
  })

  it('se anuncia como diálogo y toma el título como nombre accesible', () => {
    render(<Modal title="Editar producto" onClose={() => {}}><p>body</p></Modal>)
    expect(screen.getByRole('dialog', { name: 'Editar producto' })).toBeInTheDocument()
  })

  it('el botón de cerrar tiene nombre accesible', () => {
    render(<Modal title="Title" onClose={() => {}}><p>body</p></Modal>)
    // Antes era solo «×»: un lector de pantalla no podía nombrarlo.
    expect(screen.getByRole('button', { name: 'Cerrar' })).toBeInTheDocument()
  })

  it('lleva el foco adentro de la ventana al abrirse', () => {
    render(<Modal title="Title" onClose={() => {}}><p>body</p></Modal>)
    expect(screen.getByRole('dialog')).toHaveFocus()
  })

  /**
   * Reproduce una regresión real: el efecto que maneja el foco dependía de
   * `onClose`, que llega como función anónima y por lo tanto cambia en cada
   * render. Con un campo controlado adentro, cada tecla provocaba un render,
   * el efecto se volvía a ejecutar y `focus()` le sacaba el cursor al campo.
   * Resultado: solo entraba la primera letra de cada campo, en todos los
   * formularios del sistema que viven dentro de un modal.
   */
  it('deja escribir más de un carácter en un campo controlado', async () => {
    const usuario = userEvent.setup()

    function Formulario() {
      const [valor, setValor] = useState('')
      // onClose anónima a propósito: es como la usan todas las páginas.
      return (
        <Modal title="Alta" onClose={() => {}}>
          <input
            aria-label="Nombre"
            value={valor}
            onChange={(e) => setValor(e.target.value)}
          />
        </Modal>
      )
    }

    render(<Formulario />)
    const campo = screen.getByLabelText('Nombre')
    await usuario.click(campo)
    await usuario.keyboard('Coca Cola 500ml')

    expect(campo).toHaveValue('Coca Cola 500ml')
    expect(campo).toHaveFocus()
  })

  it('no le roba el foco al campo mientras se escribe', async () => {
    const usuario = userEvent.setup()

    function Formulario() {
      const [valor, setValor] = useState('')
      return (
        <Modal title="Alta" onClose={() => {}} disabled={valor.length > 2}>
          <input aria-label="SKU" value={valor} onChange={(e) => setValor(e.target.value)} />
        </Modal>
      )
    }

    render(<Formulario />)
    const campo = screen.getByLabelText('SKU')
    await usuario.click(campo)
    // `disabled` cambia a mitad de camino: tampoco eso debe mover el foco.
    await usuario.keyboard('ABC-123')

    expect(campo).toHaveValue('ABC-123')
    expect(campo).toHaveFocus()
  })
})
