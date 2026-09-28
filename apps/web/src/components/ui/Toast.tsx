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
  info: 'from-surface-400/70',
  success: 'from-emerald-400/70',
  error: 'from-red-400/70',
  warning: 'from-yellow-400/70',
}

const variantDot: Record<ToastVariant, string> = {
  info: 'bg-surface-400',
  success: 'bg-emerald-400',
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
          className={`clay clay-lg pointer-events-auto relative flex items-start gap-3 overflow-hidden rounded-xl px-4 py-3`}
        >
          <div
            className={`absolute inset-x-0 top-0 h-0.5 bg-gradient-to-r ${variantStyles[toast.variant]} to-transparent`}
            aria-hidden="true"
          />
          <span
            className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${variantDot[toast.variant]}`}
            aria-hidden="true"
          />
          <p className="flex-1 text-sm text-surface-100">{toast.message}</p>
          <button
            type="button"
            className="cursor-pointer rounded-md p-0.5 text-surface-400 transition-colors hover:bg-surface-800 hover:text-surface-200"
            onClick={() => dismiss(toast.id)}
            aria-label="Dismiss notification"
          >
            <svg
              className="h-4 w-4"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              aria-hidden="true"
            >
              <path d="M6 6l12 12M18 6L6 18" />
            </svg>
          </button>
        </div>
      ))}
    </div>
  )
}
