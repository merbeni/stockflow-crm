import axios from 'axios'

const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
})

// Rutas públicas: acá un 401 es una respuesta esperada del formulario y no
// debe provocar una redirección.
const RUTAS_PUBLICAS = ['/login', '/signup', '/verify-email']

function enRutaPublica() {
  if (typeof window === 'undefined') return false
  return RUTAS_PUBLICAS.some((ruta) => window.location.pathname.startsWith(ruta))
}

// Attach JWT on every request if present
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Ante un 401 se limpia el token para que PrivateRoute redirija al login.
client.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      // Sin esta condición, un login con contraseña incorrecta recargaba la
      // página y el usuario nunca llegaba a ver el mensaje de error.
      if (!enRutaPublica()) {
        window.location.href = '/login'
      }
    }
    return Promise.reject(err)
  }
)

export default client
