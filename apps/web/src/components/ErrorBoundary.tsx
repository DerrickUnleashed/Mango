import { Component, type ReactNode } from 'react'

interface State {
  hasError: boolean
  message: string | null
}

export class ErrorBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { hasError: false, message: null }

  static getDerivedStateFromError(error: unknown): State {
    return {
      hasError: true,
      message: error instanceof Error ? error.message : 'Unexpected error',
    }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div
          role="alert"
          className="flex min-h-screen items-center justify-center bg-surface-950 p-6 text-surface-50"
        >
          <div className="max-w-md">
            <h1 className="mb-2 text-2xl font-semibold">Something went wrong</h1>
            <p className="mb-4 text-surface-400">{this.state.message}</p>
            <button
              type="button"
              className="rounded-lg bg-orchard-600 px-4 py-2 font-medium text-white transition-colors hover:bg-orchard-500 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-orchard-400"
              onClick={() => window.location.reload()}
            >
              Reload application
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
