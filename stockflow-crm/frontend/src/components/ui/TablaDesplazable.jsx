import { useCallback, useEffect, useRef, useState } from 'react'

/**
 * Contenedor de tabla que avisa cuando quedan columnas fuera de la pantalla.
 *
 * En un celular las tablas entran a lo ancho solo en parte, y la columna de
 * acciones es justamente la última: quien entra desde el teléfono ve el listado
 * sin un solo botón y no tiene forma de saber que la tabla se desliza. La
 * sombra del borde es esa señal, y desaparece sola al llegar al final.
 */
export default function TablaDesplazable({ children, className = '' }) {
  const contenedor = useRef(null)
  const [sobra, setSobra] = useState({ izquierda: false, derecha: false })

  const medir = useCallback(() => {
    const el = contenedor.current
    if (!el) return
    // El margen de 1px evita que un redondeo deje la sombra encendida cuando
    // en realidad ya no queda nada para ver.
    setSobra({
      izquierda: el.scrollLeft > 1,
      derecha: el.scrollLeft + el.clientWidth < el.scrollWidth - 1,
    })
  }, [])

  useEffect(() => {
    const el = contenedor.current
    if (!el) return
    medir()
    el.addEventListener('scroll', medir, { passive: true })
    // La tabla cambia de ancho al filtrar, al cargar filas o al girar el
    // teléfono, y ninguno de esos casos dispara un scroll.
    const observador = new ResizeObserver(medir)
    observador.observe(el)
    if (el.firstElementChild) observador.observe(el.firstElementChild)
    return () => {
      el.removeEventListener('scroll', medir)
      observador.disconnect()
    }
  }, [medir])

  const borde =
    'pointer-events-none absolute inset-y-0 w-6 transition-opacity duration-200'

  return (
    <div className="relative">
      <div ref={contenedor} className={`overflow-x-auto ${className}`}>
        {children}
      </div>
      <div
        aria-hidden="true"
        className={`${borde} left-0 bg-gradient-to-r from-black/10 to-transparent ${
          sobra.izquierda ? 'opacity-100' : 'opacity-0'
        }`}
      />
      <div
        aria-hidden="true"
        className={`${borde} right-0 bg-gradient-to-l from-black/10 to-transparent ${
          sobra.derecha ? 'opacity-100' : 'opacity-0'
        }`}
      />
    </div>
  )
}
