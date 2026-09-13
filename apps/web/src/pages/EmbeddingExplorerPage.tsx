import { EmptyState } from '../components/ui/EmptyState'
import { ProcessedVideoPicker } from '../components/videos/ProcessedVideoPicker'
import { EmbeddingMap } from '../components/tracking/EmbeddingMap'
import { useProcessedVideoSelection } from '../hooks/useProcessedVideoSelection'

export function EmbeddingExplorerPage() {
  const { processed, selected, setSelected } = useProcessedVideoSelection()
  return (
    <div className="mx-auto max-w-7xl">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-surface-50">Embedding Explorer</h1>
          <p className="mt-1 text-sm text-surface-400">
            Explore per-observation embedding projections with t-SNE, PCA, and UMAP for a processed
            video.
          </p>
        </div>
        <ProcessedVideoPicker processed={processed} value={selected} onChange={setSelected} />
      </div>
      <div className="mt-6">
        {selected ? (
          <EmbeddingMap videoId={selected} enabled variant="full" />
        ) : (
          <EmptyState
            title="No embeddings to project"
            description="Process a video to visualize observation embeddings in the embedding explorer."
          />
        )}
      </div>
    </div>
  )
}
