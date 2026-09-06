/**
 * Campo de formulario con etiqueta, marca de obligatorio y error en línea.
 *
 * Centralizar el error debajo de cada input es lo que permite que el usuario
 * sepa exactamente qué corregir, en lugar de perder el formulario entero.
 */
export default function FormField({
  label,
  name,
  value,
  onChange,
  onBlur,
  error,
  hint,
  type = 'text',
  required = false,
  disabled = false,
  placeholder,
  children,
  ...rest
}) {
  const id = `campo-${name}`
  const idError = `${id}-error`
  const hayError = Boolean(error)

  return (
    <div>
      <label htmlFor={id} className="mb-1 block text-xs font-medium text-tx-secondary">
        {label}
        {required && <span className="ml-0.5 text-danger">*</span>}
      </label>

      {children ?? (
        <input
          id={id}
          name={name}
          type={type}
          value={value ?? ''}
          onChange={onChange}
          onBlur={onBlur}
          disabled={disabled}
          placeholder={placeholder}
          aria-invalid={hayError}
          aria-describedby={hayError ? idError : undefined}
          className={`w-full rounded-lg border px-3 py-1.5 text-sm focus:outline-none focus:ring-2 disabled:bg-gray-50 disabled:text-tx-muted ${
            hayError
              ? 'border-danger focus:ring-danger'
              : 'border-input-border focus:ring-secondary'
          }`}
          {...rest}
        />
      )}

      {hayError ? (
        <p id={idError} role="alert" className="mt-1 text-xs text-danger">
          {typeof error === 'string' ? error : 'El valor ingresado no es válido.'}
        </p>
      ) : (
        hint && <p className="mt-1 text-xs text-tx-muted">{hint}</p>
      )}
    </div>
  )
}
