import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { AuthContext } from '../context/AuthContext'
import Layout from './Layout'

vi.mock('../api/client', () => ({
  default: { get: vi.fn(() => Promise.resolve({ data: { name: 'Mi Empresa' } })) },
}))

function montar() {
  const auth = {
    token: 'x',
    user: { full_name: 'Ana', email: 'ana@test.com', role: 'admin' },
    isAdmin: true,
    login: vi.fn(),
    logout: vi.fn(),
  }
  return render(
    <AuthContext.Provider value={auth}>
      <MemoryRouter initialEntries={['/products']}>
        <Layout />
      </MemoryRouter>
    </AuthContext.Provider>
  )
}

describe('Menú lateral en móvil', () => {
  it('el botón alterna, no solo abre', async () => {
    // Antes hacía `setOpen(true)` siempre: con el menú abierto se anunciaba
    // como «Cerrar menú» y no cerraba nada. Con el mouse no se notaba porque el
    // cajón tapa el botón, pero por teclado sí se llega.
    const usuario = userEvent.setup()
    montar()

    const boton = screen.getByRole('button', { name: 'Abrir menú' })
    expect(boton).toHaveAttribute('aria-expanded', 'false')

    await usuario.click(boton)
    expect(boton).toHaveAttribute('aria-expanded', 'true')
    expect(boton).toHaveAccessibleName('Cerrar menú')

    await usuario.click(boton)
    expect(boton).toHaveAttribute('aria-expanded', 'false')
    expect(boton).toHaveAccessibleName('Abrir menú')
  })

  it('aria-controls apunta a un elemento que existe, también cerrado', async () => {
    // El cajón se montaba solo al abrirse, así que mientras estaba cerrado el
    // atributo señalaba un id inexistente: el lector de pantalla anuncia que el
    // botón controla algo que no puede encontrar.
    montar()
    const boton = screen.getByRole('button', { name: 'Abrir menú' })
    const id = boton.getAttribute('aria-controls')

    expect(id).toBeTruthy()
    expect(document.getElementById(id)).not.toBeNull()
  })

  it('con el menú cerrado sus enlaces no reciben el foco', async () => {
    // Montar el cajón siempre no debe dejar paradas fantasma en el recorrido
    // del Tab: se oculta con `hidden`, que sí saca del orden de tabulación.
    const usuario = userEvent.setup()
    montar()
    const boton = screen.getByRole('button', { name: 'Abrir menú' })
    const cajon = document.getElementById(boton.getAttribute('aria-controls'))

    const enlaces = cajon.querySelectorAll('a')
    expect(enlaces.length).toBeGreaterThan(0)

    await usuario.tab()
    await waitFor(() => {
      expect(cajon.contains(document.activeElement)).toBe(false)
    })
  })
})
