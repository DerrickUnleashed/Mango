import { useSearchParams } from 'react-router-dom'
import { EmptyState } from '../components/ui/EmptyState'
import { ProcessedVideoPicker } from '../components/videos/ProcessedVideoPicker'
import { IdentitiesPanel } from '../components/tracking/IdentitiesPanel'
import { useProcessedVideoSelection } from '../hooks/useProcessedVideoSelection'

export function IdentitiesPage() {
  const [searchParams] = useSearchParams()
  const videoParam = searchParams.get('video')
  const identityParam = searchParams.get('identity')
  const initialIdentityId = identityParam ? Number(identityParam) || null : null
  const { processed, selected, setSelected } = useProcessedVideoSelection(videoParam)
  return (
    <div className="mx-auto max-w-7xl">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-semibold text-surface-50">Identity Explorer</h1>
          <p className="mt-1 text-sm text-surface-400">
            Inspect individual fruit identities, their occlusion history, and quality metrics for a
            processed video.
          </p>
        </div>
        <ProcessedVideoPicker processed={processed} value={selected} onChange={setSelected} />
      </div>
      <div className="mt-6">
        {selected ? (
          <IdentitiesPanel videoId={selected} enabled initialIdentityId={initialIdentityId} />
        ) : (
          <EmptyState
            title="No identities tracked yet"
            description="Process a video to inspect individual fruit identities, their occlusion history, and quality metrics."
          />
        )}
      </div>
    </div>
  )
}
