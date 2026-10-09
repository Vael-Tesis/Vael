import { Component } from 'react'

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { error: null }
  }

  static getDerivedStateFromError(error) {
    return { error }
  }

  componentDidCatch(error, info) {
    console.error('ErrorBoundary capturó un error de renderizado:', error, info)
  }

  render() {
    if (this.state.error) {
      return (
        <div style={{
          minHeight: '100vh', display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center', padding: 24,
          background: 'var(--bg-page, #f7f7f8)', textAlign: 'center',
        }}>
          <div style={{
            width: '100%', maxWidth: 420,
            background: 'var(--bg-card, #fff)',
            border: '1px solid var(--border, #e5e5e5)',
            borderRadius: 10, padding: 32,
          }}>
            <h1 style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-primary, #111)', marginBottom: 8 }}>
              Algo salió mal
            </h1>
            <p style={{ fontSize: 13, color: 'var(--text-secondary, #555)', lineHeight: 1.5, marginBottom: 20 }}>
              Ocurrió un error inesperado y esta parte de la aplicación no pudo mostrarse.
              Puedes intentar recargar la página.
            </p>
            <button
              onClick={() => window.location.reload()}
              style={{
                height: 36, padding: '0 20px',
                background: 'var(--text-primary, #111)',
                color: 'var(--bg-card, #fff)',
                border: 'none', borderRadius: 6,
                fontSize: 13, fontWeight: 500, cursor: 'pointer',
              }}
            >
              Recargar página
            </button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
