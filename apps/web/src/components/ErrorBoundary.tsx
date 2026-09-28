import { Component, type ReactNode } from 'react'
import { LogoMark } from './ui/Logo'

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
          <div className="clay clay-lift w-full max-w-md rounded-3xl p-8 text-center">
            <LogoMark className="mx-auto h-14 w-14" />
            <h1 className="font-display mt-5 text-2xl font-semibold">Something went wrong</h1>
            <p className="mt-2 text-surface-400">{this.state.message}</p>
            <button
              type="button"
              className="bg-mango mt-6 cursor-pointer rounded-full px-6 py-2.5 font-semibold text-surface-950 clay-press-glow"
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
