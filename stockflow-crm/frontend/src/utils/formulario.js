/**
 * Utilidades para enviar formularios de edición.
 */

/**
 * Devuelve solo los campos que cambiaron respecto de cómo se abrió el formulario.
 *
 * Los formularios de edición mandaban siempre el registro completo, y eso hacía
 * que dos personas trabajando a la vez se pisaran de la peor manera: si una
 * corregía el precio de un producto y la otra, con la ficha abierta desde
 * antes, guardaba un cambio de nombre, el precio volvía al valor viejo sin que
 * nadie se enterara. Mandando únicamente lo editado, cada quien toca lo suyo y
 * el choque solo puede ocurrir si las dos editaron exactamente el mismo campo.
 *
 * La comparación es laxa a propósito: el servidor devuelve «10.00» donde el
 * formulario arma `10`, y eso no es un cambio que valga la pena enviar.
 */
export function soloLoCambiado(actual, original) {
  if (!original) return actual
  const cambios = {}
  for (const [campo, valor] of Object.entries(actual)) {
    if (!sonEquivalentes(valor, original[campo])) cambios[campo] = valor
  }
  return cambios
}

function sonEquivalentes(a, b) {
  if (a === b) return true
  // `null` y cadena vacía representan lo mismo en los campos opcionales.
  if ((a ?? '') === '' && (b ?? '') === '') return true
  const numeroA = Number(a)
  const numeroB = Number(b)
  if (a !== '' && b !== '' && a != null && b != null &&
      !Number.isNaN(numeroA) && !Number.isNaN(numeroB)) {
    return numeroA === numeroB
  }
  return false
}
