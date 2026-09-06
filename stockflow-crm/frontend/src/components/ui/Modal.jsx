import { useEffect, useId, useRef } from 'react'

/**
 * Ventana modal accesible.
 *
 * Además de mostrar el contenido, se ocupa de tres cosas que un `div` flotante
 * no resuelve solo y que son las que hacen que la ventana sea usable sin mouse:
 *
 *   1. Se cierra con la tecla Escape, que es lo primero que prueba quien quiere
 *      salir de una ventana emergente.
 *   2. Se anuncia como diálogo y toma el título como nombre accesible, para que
 *      un lector de pantalla diga de qué ventana se trata.
 *   3. Lleva el foco adentro al abrirse, lo retiene mientras está abierta y lo
 *      devuelve al cerrarse, así quien navega con Tab no termina en la página
 *      que quedó detrás del velo.
 *
 * Cuando `disabled` está activo hay una operación en curso: cerrar a mitad de
 * camino dejaría al usuario sin saber si se guardó, así que la tecla Escape se
 * ignora.
 *
 * A propósito **no** se cierra al hacer clic en el fondo. Casi todas estas
 * ventanas contienen un formulario a medio completar, y un clic al costado es
 * fácil de hacer sin querer: perder lo cargado por eso es peor que tener que
 * apuntar a «Cancelar».
 */
// Lo que puede recibir el foco con Tab dentro de la ventana.
const ENFOCABLES =
  'a[href], button, input, select, textarea, [tabindex]:not([tabindex="-1"])'

export default function Modal({ title, onClose, children, disabled = false }) {
  const idTitulo = useId()
  const contenedor = useRef(null)

  // `onClose` suele llegar como función anónima («onClose={() => setModal(null)}»),
  // así que es distinta en cada render. Guardarla en una referencia permite que
  // los efectos de abajo no dependan de ella y se ejecuten una sola vez.
  const alCerrar = useRef(onClose)
  const bloqueado = useRef(disabled)
  useEffect(() => {
    alCerrar.current = onClose
    bloqueado.current = disabled
  })

  /**
   * Foco: entra al abrir, vuelve a su lugar al cerrar.
   *
   * Este efecto tiene que correr **una sola vez**. Cuando dependía de `onClose`
   * volvía a ejecutarse en cada render —o sea, con cada tecla— y `focus()` le
   * sacaba el cursor al campo que la persona estaba completando: solo entraba
   * la primera letra de cada uno.
   */
  useEffect(() => {
    const anterior = document.activeElement
    contenedor.current?.focus()
    return () => {
      if (anterior instanceof HTMLElement) anterior.focus()
    }
  }, [])

  useEffect(() => {
    /**
     * Devuelve los controles de la ventana que hoy pueden recibir el foco.
     *
     * Se descartan los deshabilitados y los ocultos: un campo escondido sigue
     * estando en el DOM, pero tabular hasta él dejaría el foco en un lugar que
     * no se ve. La comprobación mira los estilos y no las medidas de layout,
     * que son cero en cualquier entorno sin motor de render.
     */
    function enfocables() {
      const caja = contenedor.current
      if (!caja) return []
      return [...caja.querySelectorAll(ENFOCABLES)].filter((el) => {
        if (el.disabled || el.closest('[hidden]')) return false
        const estilo = window.getComputedStyle(el)
        return estilo.display !== 'none' && estilo.visibility !== 'hidden'
      })
    }

    function alPresionar(evento) {
      if (evento.key === 'Escape' && !bloqueado.current) {
        evento.stopPropagation()
        alCerrar.current()
        return
      }

      // Sin esto, un Tab desde el último control salta a la página que quedó
      // detrás del velo: el foco se va al menú lateral, que no se ve y no se
      // puede usar, y un Enter ahí navega a otra pantalla perdiendo lo cargado.
      if (evento.key !== 'Tab') return
      const lista = enfocables()
      if (lista.length === 0) {
        evento.preventDefault()
        contenedor.current?.focus()
        return
      }

      const primero = lista[0]
      const ultimo = lista[lista.length - 1]
      const actual = document.activeElement
      const afuera = !contenedor.current?.contains(actual)

      if (evento.shiftKey && (actual === primero || afuera)) {
        evento.preventDefault()
        ultimo.focus()
      } else if (!evento.shiftKey && (actual === ultimo || afuera)) {
        evento.preventDefault()
        primero.focus()
      }
    }

    document.addEventListener('keydown', alPresionar)
    return () => document.removeEventListener('keydown', alPresionar)
  }, [])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div
        ref={contenedor}
        role="dialog"
        aria-modal="true"
        aria-labelledby={idTitulo}
        tabIndex={-1}
        className="bg-surface rounded-2xl shadow-xl w-full max-w-lg mx-4 max-h-[90vh] flex flex-col border border-brand-border focus:outline-none"
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-brand-border">
          <h2 id={idTitulo} className="text-base font-semibold text-tx-primary">
            {title}
          </h2>
          <button
            type="button"
            onClick={onClose}
            disabled={disabled}
            aria-label="Cerrar"
            className="text-tx-muted hover:text-tx-secondary text-xl leading-none disabled:opacity-30 disabled:cursor-not-allowed"
          >
            &times;
          </button>
        </div>
        <div className="overflow-y-auto px-6 py-4 flex-1">{children}</div>
      </div>
    </div>
  )
}
