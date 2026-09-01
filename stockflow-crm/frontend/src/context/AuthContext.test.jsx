import { render, screen, act, waitFor } from '@testing-library/react'
import { AuthProvider, useAuth } from './AuthContext'

// ── mock del cliente axios ───────────────────────────────────────────────────
vi.mock('../api/client', () => ({
  default: {
    post: vi.fn(),
    get: vi.fn(),
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
  },
}))

import client from '../api/client'

function TestConsumer() {
  const { token, user, isAdmin, login, logout } = useAuth()
  return (
    <div>
      <span data-testid="token">{token ?? 'null'}</span>
      <span data-testid="user">{user?.email ?? 'null'}</span>
      <span data-testid="admin">{String(isAdmin)}</span>
      <button onClick={() => login('a@test.com', 'pass')}>Login</button>
      <button onClick={logout}>Logout</button>
    </div>
  )
}

function renderProvider() {
  return render(
    <AuthProvider>
      <TestConsumer />
    </AuthProvider>
  )
}

beforeEach(() => {
  localStorage.clear()
  vi.clearAllMocks()
  client.get.mockResolvedValue({ data: { email: 'a@test.com', role: 'operator' } })
})

describe('AuthProvider', () => {
  it('arranca sin token cuando localStorage está vacío', () => {
    renderProvider()
    expect(screen.getByTestId('token').textContent).toBe('null')
  })

  it('lee el token de localStorage al montar', () => {
    localStorage.setItem('token', 'stored-token')
    renderProvider()
    expect(screen.getByTestId('token').textContent).toBe('stored-token')
  })

  it('recupera el perfil al montar con un token guardado', async () => {
    // Antes el perfil se perdía al recargar la página y el nombre del usuario
    // quedaba vacío en la barra lateral.
    localStorage.setItem('token', 'stored-token')
    renderProvider()
    await waitFor(() =>
      expect(screen.getByTestId('user').textContent).toBe('a@test.com')
    )
    expect(client.get).toHaveBeenCalledWith('/auth/me')
  })

  it('cierra la sesión si el perfil no se puede recuperar', async () => {
    localStorage.setItem('token', 'token-vencido')
    client.get.mockRejectedValue(new Error('401'))
    renderProvider()
    await waitFor(() => expect(screen.getByTestId('token').textContent).toBe('null'))
    expect(localStorage.getItem('token')).toBeNull()
  })

  it('el login guarda el token y trae el perfil', async () => {
    client.post.mockResolvedValue({ data: { access_token: 'new-token' } })

    renderProvider()
    await act(async () => {
      screen.getByText('Login').click()
    })

    expect(localStorage.getItem('token')).toBe('new-token')
    expect(screen.getByTestId('token').textContent).toBe('new-token')
    await waitFor(() =>
      expect(screen.getByTestId('user').textContent).toBe('a@test.com')
    )
  })

  it('expone isAdmin según el rol del usuario', async () => {
    localStorage.setItem('token', 'tok')
    client.get.mockResolvedValue({ data: { email: 'jefe@test.com', role: 'admin' } })
    renderProvider()
    await waitFor(() => expect(screen.getByTestId('admin').textContent).toBe('true'))
  })

  it('el logout limpia el token y el usuario', async () => {
    client.post.mockResolvedValue({ data: { access_token: 'tok' } })

    renderProvider()
    await act(async () => {
      screen.getByText('Login').click()
    })
    await waitFor(() => expect(screen.getByTestId('token').textContent).toBe('tok'))

    act(() => {
      screen.getByText('Logout').click()
    })

    expect(localStorage.getItem('token')).toBeNull()
    expect(screen.getByTestId('token').textContent).toBe('null')
    expect(screen.getByTestId('user').textContent).toBe('null')
  })
})
