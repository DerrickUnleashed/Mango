interface EmptyStateProps {
  title: string
  description: string
}

export function EmptyState({ title, description }: EmptyStateProps) {
  return (
    <div
      className="rounded-xl border border-surface-800 bg-surface-900/40 p-10 text-center"
      role="status"
    >
      <p className="font-medium text-surface-300">{title}</p>
      <p className="mx-auto mt-2 max-w-md text-sm text-surface-500">{description}</p>
    </div>
  )
}
