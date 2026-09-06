/**
 * Banner de error reutilizable.
 *
 * Fuerza el contenido a string: si por cualquier motivo llegara un objeto,
 * se muestra un mensaje genérico en lugar de romper el render de React.
 */
export default function ErrorBanner({ message, onDismiss, className = '' }) {
  if (!message) return null

  const texto =
    typeof message === 'string'
      ? message
      : 'Ocurrió un error inesperado. Por favor intentá nuevamente.'

  return (
    <div
      role="alert"
      className={`flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 ${className}`}
    >
      <svg
        className="mt-0.5 h-4 w-4 shrink-0 text-danger"
        fill="none"
        stroke="currentColor"
        strokeWidth={2}
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M12 9v4m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"
        />
      </svg>
      <p className="flex-1 text-sm text-red-700">{texto}</p>
      {onDismiss && (
        <button
          type="button"
          onClick={onDismiss}
          aria-label="Cerrar aviso"
          className="shrink-0 text-lg leading-none text-danger hover:text-danger"
        >
          &times;
        </button>
      )}
    </div>
  )
}
