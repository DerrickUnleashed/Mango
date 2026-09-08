import { EmptyState } from '../components/ui/EmptyState'

export function EvaluationPage() {
  return (
    <div className="mx-auto max-w-7xl">
      <h1 className="text-2xl font-semibold text-surface-50">Evaluation</h1>
      <div className="mt-6">
        <EmptyState
          title="No evaluations yet"
          description="Run experiments to compare IDF1, HOTA, recovery rate, and counting accuracy against ByteTrack, SORT, and DeepSORT baselines."
        />
      </div>
    </div>
  )
}