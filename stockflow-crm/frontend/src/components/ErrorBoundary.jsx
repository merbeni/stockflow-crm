import { Component } from 'react'

/**
 * Red de seguridad de la aplicación.
 *
 * Antes, cualquier excepción durante el render (por ejemplo intentar mostrar el
 * `detail` de un error 422, que es una lista de objetos) desmontaba todo el
 * árbol y dejaba la pantalla en blanco, sin ninguna forma de recuperarse salvo
 * refrescando el navegador. Este límite captura esos fallos y ofrece una salida.
 */
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  componentDidCatch(error, info) {
    console.error('Error no controlado en la interfaz:', error, info)
  }

  handleRetry = () => {
    this.setState({ hasError: false })
  }

  render() {
    if (!this.state.hasError) return this.props.children

    return (
      <div className="flex min-h-screen items-center justify-center bg-page p-4">
        <div className="w-full max-w-md rounded-2xl border border-brand-border bg-surface p-8 text-center shadow">
          <h1 className="mb-2 text-lg font-bold text-tx-primary">
            Algo salió mal
          </h1>
          <p className="mb-6 text-sm text-tx-muted">
            Ocurrió un error inesperado al mostrar esta pantalla. Podés
            reintentar o volver al inicio.
          </p>
          <div className="flex justify-center gap-2">
            <button
              onClick={this.handleRetry}
              className="rounded-lg bg-secondary px-4 py-2 text-sm font-medium text-secondary-text transition hover:bg-secondary-dark"
            >
              Reintentar
            </button>
            <button
              onClick={() => {
                window.location.href = '/'
              }}
              className="rounded-lg border border-input-border px-4 py-2 text-sm hover:bg-sidebar"
            >
              Ir al inicio
            </button>
          </div>
        </div>
      </div>
    )
  }
}
