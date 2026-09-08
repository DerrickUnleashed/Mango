import { EmptyState } from '../components/ui/EmptyState'

export function ExperimentsPage() {
  return (
    <div className="mx-auto max-w-7xl">
      <h1 className="text-2xl font-semibold text-surface-50">Experiments</h1>
      <div className="mt-6">
        <EmptyState
          title="No experiments created"
          description="Create experiments to study occlusion duration, viewpoint changes, and camera motion on identity recovery."
        />
      </div>
    </div>
  )
}