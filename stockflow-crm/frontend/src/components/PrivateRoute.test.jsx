import { render, screen } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { AuthContext } from '../context/AuthContext'
import PrivateRoute from './PrivateRoute'

// Helper to render PrivateRoute with a given token value
function renderWithAuth(token) {
  return render(
    <AuthContext.Provider value={{ token, user: null, login: vi.fn(), logout: vi.fn() }}>
      <MemoryRouter initialEntries={['/dashboard']}>
        <Routes>
          <Route path="/login" element={<div>Login Page</div>} />
          <Route
            path="/dashboard"
            element={
              <PrivateRoute>
                <div>Protected Content</div>
              </PrivateRoute>
            }
          />
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>
  )
}

describe('PrivateRoute', () => {
  it('renders children when token exists', () => {
    renderWithAuth('valid-token')
    expect(screen.getByText('Protected Content')).toBeInTheDocument()
  })

  it('redirects to /login when token is null', () => {
    renderWithAuth(null)
    expect(screen.getByText('Login Page')).toBeInTheDocument()
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument()
  })

  it('redirects to /login when token is empty string', () => {
    renderWithAuth('')
    expect(screen.getByText('Login Page')).toBeInTheDocument()
  })
})
