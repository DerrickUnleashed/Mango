import { ExperimentsView } from './ExperimentsPage'

export function EvaluationPage() {
  return (
    <div className="mx-auto max-w-7xl">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-display text-2xl font-semibold text-surface-50">Evaluation</h1>
          <p className="mt-1 text-sm text-surface-400">
            Compare IDF1, HOTA, recovery rate, and counting accuracy across mock and ByteTrack
            baselines from the experiment harness.
          </p>
        </div>
      </div>
      <ExperimentsView />
    </div>
  )
}
