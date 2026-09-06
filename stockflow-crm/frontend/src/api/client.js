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

/**
 * Parámetros con los que el interceptor le cuenta al login qué pasó.
 *
 * Van en la URL y no en `sessionStorage` porque la redirección de abajo es una
 * navegación completa: mientras el navegador la resuelve, React alcanza a
 * montar el login dentro de la página vieja, ese login consume la marca y se
 * destruye enseguida. El aviso terminaba perdiéndose siempre.
 */
export const PARAM_EXPIRADA = 'expirada'
export const PARAM_VOLVER = 'volver'

// Ante un 401 se limpia el token para que PrivateRoute redirija al login.
client.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      // Sin esta condición, un login con contraseña incorrecta recargaba la
      // página y el usuario nunca llegaba a ver el mensaje de error.
      if (!enRutaPublica()) {
        // Antes se caía al login sin ninguna explicación: quien estaba
        // trabajando veía desaparecer la pantalla y no sabía si se había roto
        // algo o si había hecho algo mal.
        const destino = window.location.pathname + window.location.search
        const parametros = new URLSearchParams({
          [PARAM_EXPIRADA]: '1',
          [PARAM_VOLVER]: destino,
        })
        window.location.href = `/login?${parametros}`
      }
    }
    return Promise.reject(err)
  }
)

export default client
