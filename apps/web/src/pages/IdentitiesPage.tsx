import { EmptyState } from '../components/ui/EmptyState'

export function IdentitiesPage() {
  return (
    <div className="mx-auto max-w-7xl">
      <h1 className="text-2xl font-semibold text-surface-50">Identity Explorer</h1>
      <div className="mt-6">
        <EmptyState
          title="No identities tracked yet"
          description="Process a video to inspect individual fruit identities, their occlusion history, and quality metrics."
        />
      </div>
    </div>
  )
}
