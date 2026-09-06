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
 *   3. Lleva el foco adentro al abrirse y lo devuelve al cerrarse, así quien
 *      navega con Tab no queda recorriendo la página que está detrás.
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
export default function Modal({ title, onClose, children, disabled = false }) {
  const idTitulo = useId()
  const contenedor = useRef(null)

  useEffect(() => {
    const anterior = document.activeElement

    function alPresionar(evento) {
      if (evento.key === 'Escape' && !disabled) {
        evento.stopPropagation()
        onClose()
      }
    }

    document.addEventListener('keydown', alPresionar)
    contenedor.current?.focus()

    return () => {
      document.removeEventListener('keydown', alPresionar)
      // Devolver el foco a donde estaba evita que vuelva al principio del documento.
      if (anterior instanceof HTMLElement) anterior.focus()
    }
  }, [onClose, disabled])

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
