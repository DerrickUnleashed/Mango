import { EmptyState } from '../components/ui/EmptyState'
import { ProcessedVideoPicker } from '../components/videos/ProcessedVideoPicker'
import { AnalyticsPanel } from '../components/tracking/AnalyticsPanel'
import { useProcessedVideoSelection } from '../hooks/useProcessedVideoSelection'

export function AnalyticsPage() {
  const { processed, selected, setSelected } = useProcessedVideoSelection()
  return (
    <div className="mx-auto max-w-7xl">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-semibold text-surface-50">Analytics</h1>
          <p className="mt-1 text-sm text-surface-400">
            Frame-wise fruit counts, track statistics, and occlusion patterns for a processed video.
          </p>
        </div>
        <ProcessedVideoPicker processed={processed} value={selected} onChange={setSelected} />
      </div>
      <div className="mt-6">
        {selected ? (
          <AnalyticsPanel videoId={selected} enabled />
        ) : (
          <EmptyState
            title="Analytics will appear here"
            description="Process a video to see frame-wise fruit counts, track statistics, and occlusion patterns."
          />
        )}
      </div>
    </div>
  )
}
