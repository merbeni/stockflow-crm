import { createContext, useContext, useState } from 'react'
import client from '../api/client'

export const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem('token'))
  const [user, setUser] = useState(null)

  async function login(email, password) {
    const { data } = await client.post('/auth/login', { email, password })
    localStorage.setItem('token', data.access_token)
    setToken(data.access_token)
    // Fetch user profile
    const me = await client.get('/auth/me')
    setUser(me.data)
    return me.data
  }

  function logout() {
    localStorage.removeItem('token')
    setToken(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ token, user, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
