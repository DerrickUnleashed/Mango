import { EmptyState } from '../components/ui/EmptyState'

export function AnalyticsPage() {
  return (
    <div className="mx-auto max-w-7xl">
      <h1 className="text-2xl font-semibold text-surface-50">Analytics</h1>
      <div className="mt-6">
        <EmptyState
          title="Analytics will appear here"
          description="Process a video to see frame-wise fruit counts, track statistics, and occlusion patterns."
        />
      </div>
    </div>
  )
}
