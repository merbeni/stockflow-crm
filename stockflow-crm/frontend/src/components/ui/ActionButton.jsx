/**
 * Botón de acción de una fila de tabla.
 *
 * Antes eran textos subrayados, todos con el mismo peso visual: había que
 * leerlos para saber cuál borraba. Ahora cada verbo tiene su color, y el color
 * significa siempre lo mismo en todo el sistema:
 *
 *   consultar  → gris    · no cambia nada, solo muestra información
 *   editar     → azul    · cambia datos, se puede volver atrás
 *   activar    → verde   · devuelve algo al uso
 *   rol        → violeta · cambia permisos: quién puede hacer qué
 *   desactivar → ámbar   · lo saca de circulación, es reversible
 *   eliminar   → rojo    · destruye, no se puede deshacer
 *
 * El violeta tiene tono propio porque cambiar el rol y desactivar la cuenta son
 * cosas distintas —permisos contra disponibilidad— y compartiendo el ámbar
 * quedaban dos botones idénticos uno al lado del otro en la fila de usuarios.
 *
 * El gris de «consultar» no es falta de criterio: es la ausencia de riesgo. Si
 * todas las acciones tuvieran un color fuerte, ninguno destacaría y el rojo
 * dejaría de ser una advertencia.
 *
 * El color acompaña al texto, nunca lo reemplaza: quien no distingue el rojo
 * del ámbar sigue leyendo «Eliminar» y «Desactivar». Los ratios de contraste
 * están verificados y anotados en `index.css`.
 */
const TONOS = {
  consultar: 'border-gray-300 bg-gray-50 text-tx-secondary',
  editar: 'border-act-edit-border bg-act-edit-bg text-act-edit-text',
  activar: 'border-act-on-border bg-act-on-bg text-act-on-text',
  rol: 'border-act-role-border bg-act-role-bg text-act-role-text',
  desactivar: 'border-act-off-border bg-act-off-bg text-act-off-text',
  eliminar: 'border-act-del-border bg-act-del-bg text-act-del-text',
}
// «Avanzar un pedido» comparte el verde con «activar»: las dos habilitan algo.
// El alias existe para que el nombre en el código diga lo que hace la acción.
TONOS.avanzar = TONOS.activar

const BASE =
  'inline-flex items-center rounded-md border px-2.5 py-1 text-xs font-medium ' +
  'transition hover:brightness-95 active:brightness-90 ' +
  'disabled:cursor-not-allowed disabled:border-gray-200 disabled:bg-gray-50 ' +
  'disabled:text-gray-400 disabled:hover:brightness-100'

export default function ActionButton({
  tono = 'editar',
  children,
  className = '',
  ...rest
}) {
  return (
    <button type="button" className={`${BASE} ${TONOS[tono]} ${className}`} {...rest}>
      {children}
    </button>
  )
}
