import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import client from '../api/client'

export const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem('token'))
  const [user, setUser] = useState(null)
  // Mientras se recupera el perfil no se sabe si la sesión sigue siendo válida.
  const [loading, setLoading] = useState(() => Boolean(localStorage.getItem('token')))

  const logout = useCallback(() => {
    localStorage.removeItem('token')
    setToken(null)
    setUser(null)
  }, [])

  // Al recargar la página el token sigue en localStorage pero el perfil se
  // perdía, así que el nombre del usuario y su rol quedaban vacíos.
  useEffect(() => {
    if (!token) {
      setUser(null)
      setLoading(false)
      return
    }
    let cancelado = false
    setLoading(true)
    client
      .get('/auth/me')
      .then(({ data }) => {
        if (!cancelado) setUser(data)
      })
      .catch(() => {
        if (!cancelado) logout()
      })
      .finally(() => {
        if (!cancelado) setLoading(false)
      })
    return () => {
      cancelado = true
    }
  }, [token, logout])

  async function login(email, password) {
    const { data } = await client.post('/auth/login', { email, password })
    localStorage.setItem('token', data.access_token)
    setToken(data.access_token)
    const me = await client.get('/auth/me')
    setUser(me.data)
    return me.data
  }

  const isAdmin = user?.role === 'admin'

  return (
    <AuthContext.Provider value={{ token, user, loading, isAdmin, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
