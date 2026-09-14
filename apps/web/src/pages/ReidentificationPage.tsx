import { EmptyState } from '../components/ui/EmptyState'
import { ProcessedVideoPicker } from '../components/videos/ProcessedVideoPicker'
import { ReIdPanel } from '../components/tracking/ReIdPanel'
import { useProcessedVideoSelection } from '../hooks/useProcessedVideoSelection'

export function ReidentificationPage() {
  const { processed, selected, setSelected } = useProcessedVideoSelection()
  return (
    <div className="mx-auto max-w-7xl">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-semibold text-surface-50">Re-Identification</h1>
          <p className="mt-1 text-sm text-surface-400">
            Occlusion events and identity recovery timelines for a processed video.
          </p>
        </div>
        <ProcessedVideoPicker processed={processed} value={selected} onChange={setSelected} />
      </div>
      <div className="mt-6">
        {selected ? (
          <ReIdPanel videoId={selected} enabled />
        ) : (
          <EmptyState
            title="No re-identification events"
            description="After processing, view occlusion events and identity recovery timelines here."
          />
        )}
      </div>
    </div>
  )
}
