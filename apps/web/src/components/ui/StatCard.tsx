interface StatCardProps {
  label: string
  value: string | number
  hint?: string
  accent?: 'default' | 'positive' | 'warning'
}

const accentClasses: Record<NonNullable<StatCardProps['accent']>, string> = {
  default: 'text-surface-50',
  positive: 'text-emerald-300',
  warning: 'text-orchard-300',
}

const accentBar: Record<NonNullable<StatCardProps['accent']>, string> = {
  default: 'from-orchard-400/60 to-transparent',
  positive: 'from-emerald-400/60 to-transparent',
  warning: 'from-orchard-300/70 to-transparent',
}

export function StatCard({ label, value, hint, accent = 'default' }: StatCardProps) {
  return (
    <div className="clay clay-lift relative cursor-pointer overflow-hidden rounded-2xl p-5">
      <div
        className={`pointer-events-none absolute inset-x-3 top-0 h-1 rounded-full bg-gradient-to-r ${accentBar[accent]}`}
        aria-hidden="true"
      />
      <p className="text-xs font-medium tracking-wide text-surface-400 uppercase">{label}</p>
      <p
        className={`font-display mt-2 text-3xl font-semibold tabular-nums ${accentClasses[accent]}`}
      >
        {value}
      </p>
      {hint && <p className="mt-1 text-xs text-surface-500">{hint}</p>}
    </div>
  )
}
