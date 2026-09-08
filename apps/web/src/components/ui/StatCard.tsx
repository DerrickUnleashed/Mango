interface StatCardProps {
  label: string
  value: string | number
  hint?: string
  accent?: 'default' | 'positive' | 'warning'
}

const accentClasses: Record<NonNullable<StatCardProps['accent']>, string> = {
  default: 'text-surface-50',
  positive: 'text-orchard-300',
  warning: 'text-yellow-300',
}

export function StatCard({ label, value, hint, accent = 'default' }: StatCardProps) {
  return (
    <div className="rounded-xl border border-surface-800 bg-surface-900/60 p-4">
      <p className="text-xs font-medium tracking-wide text-surface-500 uppercase">{label}</p>
      <p className={`mt-2 text-3xl font-semibold tabular-nums ${accentClasses[accent]}`}>{value}</p>
      {hint && <p className="mt-1 text-xs text-surface-600">{hint}</p>}
    </div>
  )
}