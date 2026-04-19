import { render, screen, fireEvent } from '@testing-library/react'
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
})
