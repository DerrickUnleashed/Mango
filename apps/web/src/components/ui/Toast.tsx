import { useCallback, useMemo, useState, type ReactNode } from 'react'
import { ToastContext, useToast } from './useToast'

export type ToastVariant = 'info' | 'success' | 'error' | 'warning'

export interface Toast {
  id: number
  message: string
  variant: ToastVariant
}

let nextId = 1

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])

  const dismiss = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const push = useCallback(
    (message: string, variant: ToastVariant = 'info') => {
      const id = nextId++
      setToasts((prev) => [...prev.slice(-4), { id, message, variant }])
      window.setTimeout(() => dismiss(id), 6000)
    },
    [dismiss],
  )

  const value = useMemo(() => ({ toasts, push, dismiss }), [toasts, push, dismiss])

  return <ToastContext.Provider value={value}>{children}</ToastContext.Provider>
}

const variantStyles: Record<ToastVariant, string> = {
  info: 'border-surface-700 bg-surface-800 text-surface-100',
  success: 'border-orchard-700 bg-orchard-900 text-orchard-100',
  error: 'border-red-800 bg-red-950 text-red-100',
  warning: 'border-yellow-800 bg-yellow-950 text-yellow-100',
}

const variantDot: Record<ToastVariant, string> = {
  info: 'bg-surface-400',
  success: 'bg-orchard-400',
  error: 'bg-red-400',
  warning: 'bg-yellow-400',
}

export function Toaster() {
  const { toasts, dismiss } = useToast()
  return (
    <div
      className="pointer-events-none fixed right-4 bottom-4 z-50 flex w-80 flex-col gap-2"
      role="region"
      aria-label="Notifications"
    >
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={`pointer-events-auto flex items-start gap-3 rounded-lg border px-4 py-3 shadow-lg ${variantStyles[toast.variant]}`}
        >
          <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${variantDot[toast.variant]}`} aria-hidden="true" />
          <p className="flex-1 text-sm">{toast.message}</p>
          <button
            type="button"
            className="text-surface-400 hover:text-surface-200"
            onClick={() => dismiss(toast.id)}
            aria-label="Dismiss notification"
          >
            ✕
          </button>
        </div>
      ))}
    </div>
  )
}