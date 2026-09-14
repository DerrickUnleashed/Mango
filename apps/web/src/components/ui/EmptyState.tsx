interface EmptyStateProps {
  title: string
  description: string
}

export function EmptyState({ title, description }: EmptyStateProps) {
  return (
    <div
      className="glass card-glow rounded-2xl p-10 text-center"
      role="status"
    >
      <div className="bg-mango mx-auto flex h-12 w-12 items-center justify-center rounded-2xl opacity-90">
        <svg
          className="h-6 w-6 text-surface-950"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <path d="M3 21h18M4 21v-7a8 8 0 0 1 16 0v7M12 8V3M8 8l4-3 4 3" />
        </svg>
      </div>
      <p className="mt-4 font-medium text-surface-200">{title}</p>
      <p className="mx-auto mt-2 max-w-md text-sm text-surface-500">{description}</p>
    </div>
  )
}