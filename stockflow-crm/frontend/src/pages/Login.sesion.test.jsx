/**
 * Qué ve alguien cuando se le corta la sesión mientras estaba trabajando.
 *
 * El aviso viajaba en `sessionStorage` y nunca llegaba a verse: la redirección
 * del interceptor es una navegación completa, y mientras el navegador la
 * resolvía React alcanzaba a montar este login dentro de la página vieja. Ese
 * login consumía la marca y se destruía enseguida, así que el login definitivo
 * aparecía sin ninguna explicación.
 */
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { AuthContext } from '../context/AuthContext'
import Login from './Login'

vi.mock('../api/client', async () => {
  const real = await vi.importActual('../api/client')
  return { ...real, default: { post: vi.fn() } }
})

function montar(ruta, login = vi.fn()) {
  return render(
    <AuthContext.Provider value={{ login, token: null, user: null }}>
      <MemoryRouter initialEntries={[ruta]}>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/stock-movements" element={<h1>Movimientos de stock</h1>} />
          <Route path="/" element={<h1>Inicio</h1>} />
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>
  )
}

const AVISO = /sesión se cerró por inactividad/i

// Sin `delay: null`, userEvent espera entre tecla y tecla: con la máquina
// cargada, escribir correo y contraseña más la navegación posterior rozaba el
// límite de espera y la prueba fallaba de a ratos. Acá lo que se verifica es a
// dónde lleva el ingreso, no la velocidad de tipeo.

describe('Aviso de sesión vencida', () => {
  it('explica por qué apareció el login', () => {
    montar('/login?expirada=1&volver=%2Fstock-movements')
    expect(screen.getByText(AVISO)).toBeInTheDocument()
  })

  it('no aparece cuando se entra al login por voluntad propia', () => {
    montar('/login')
    expect(screen.queryByText(AVISO)).not.toBeInTheDocument()
  })

  it('devuelve a la pantalla donde estaba trabajando', async () => {
    const usuario = userEvent.setup({ delay: null })
    montar('/login?expirada=1&volver=%2Fstock-movements')

    await usuario.type(screen.getByLabelText(/correo/i), 'ana@test.com')
    await usuario.type(screen.getByLabelText(/contraseña/i), 'Clave123!')
    await usuario.click(screen.getByRole('button', { name: /ingresar/i }))

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Movimientos de stock' })).toBeInTheDocument()
    })
  })

  it('ignora un destino externo en lugar de seguirlo', async () => {
    // Un `volver` con una URL completa sería un redirect abierto: bastaría
    // mandarle a alguien un enlace al login propio para dejarlo, después de
    // entrar, en un sitio ajeno con aspecto de ser el sistema.
    const usuario = userEvent.setup({ delay: null })
    montar('/login?expirada=1&volver=https%3A%2F%2Fsitio-ajeno.example')

    await usuario.type(screen.getByLabelText(/correo/i), 'ana@test.com')
    await usuario.type(screen.getByLabelText(/contraseña/i), 'Clave123!')
    await usuario.click(screen.getByRole('button', { name: /ingresar/i }))

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Inicio' })).toBeInTheDocument()
    })
  })

  it('tampoco sigue un destino con doble barra, que el navegador lee como otro dominio', async () => {
    const usuario = userEvent.setup({ delay: null })
    montar('/login?expirada=1&volver=%2F%2Fsitio-ajeno.example')

    await usuario.type(screen.getByLabelText(/correo/i), 'ana@test.com')
    await usuario.type(screen.getByLabelText(/contraseña/i), 'Clave123!')
    await usuario.click(screen.getByRole('button', { name: /ingresar/i }))

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Inicio' })).toBeInTheDocument()
    })
  })
})
