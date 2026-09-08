import { EmptyState } from '../components/ui/EmptyState'

export function ReidentificationPage() {
  return (
    <div className="mx-auto max-w-7xl">
      <h1 className="text-2xl font-semibold text-surface-50">Re-Identification</h1>
      <div className="mt-6">
        <EmptyState
          title="No re-identification events"
          description="After processing, view occlusion events and identity recovery timelines here."
        />
      </div>
    </div>
  )
}