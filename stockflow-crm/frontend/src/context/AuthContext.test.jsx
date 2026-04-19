import { render, screen, act, waitFor } from '@testing-library/react'
import { AuthProvider, useAuth } from './AuthContext'

// ── mock the axios client ────────────────────────────────────────────────────
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

// Helper component that exposes auth context values for assertions
function TestConsumer() {
  const { token, user, login, logout } = useAuth()
  return (
    <div>
      <span data-testid="token">{token ?? 'null'}</span>
      <span data-testid="user">{user?.email ?? 'null'}</span>
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
})

describe('AuthProvider', () => {
  it('starts with null token when localStorage is empty', () => {
    renderProvider()
    expect(screen.getByTestId('token').textContent).toBe('null')
  })

  it('reads token from localStorage on mount', () => {
    localStorage.setItem('token', 'stored-token')
    renderProvider()
    expect(screen.getByTestId('token').textContent).toBe('stored-token')
  })

  it('login stores token and fetches user', async () => {
    client.post.mockResolvedValue({ data: { access_token: 'new-token' } })
    client.get.mockResolvedValue({ data: { email: 'a@test.com', role: 'operator' } })

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

  it('logout clears token and user', async () => {
    client.post.mockResolvedValue({ data: { access_token: 'tok' } })
    client.get.mockResolvedValue({ data: { email: 'a@test.com' } })

    renderProvider()
    await act(async () => { screen.getByText('Login').click() })
    await waitFor(() => expect(screen.getByTestId('token').textContent).toBe('tok'))

    act(() => { screen.getByText('Logout').click() })

    expect(localStorage.getItem('token')).toBeNull()
    expect(screen.getByTestId('token').textContent).toBe('null')
    expect(screen.getByTestId('user').textContent).toBe('null')
  })
})
