import { useMotionEstimate } from '../../hooks/useVideos'

interface MotionPanelProps {
  videoId: string
  enabled: boolean
}

export function MotionPanel({ videoId, enabled }: MotionPanelProps) {
  const { data: estimate, isLoading, isError } = useMotionEstimate(videoId, enabled)

  if (!enabled) return null

  const isDrifting = Boolean(estimate && estimate.meanAbsShift > 1e-6)

  return (
    <div className="rounded-xl border border-surface-800 bg-surface-950 p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="font-medium text-surface-200">Camera motion</h2>
          <p className="mt-1 text-sm text-surface-400">
            How much the camera drifts between frames, and whether tracking compensates for it.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span
            className={`rounded-full px-2.5 py-1 text-xs font-medium ${
              isDrifting
                ? 'bg-amber-500/15 text-amber-300'
                : 'bg-emerald-500/15 text-emerald-300'
            }`}
          >
            {isDrifting ? 'Drifting camera' : 'Static camera'}
          </span>
        </div>
      </div>

      {isLoading && <p className="mt-4 text-sm text-surface-500">Loading estimate…</p>}
      {isError && (
        <p className="mt-4 text-sm text-red-400">Failed to load camera motion estimate.</p>
      )}
      {!isLoading && !isError && estimate === null && (
        <p className="mt-4 text-sm text-surface-500">
          No estimate yet — run processing to measure camera motion.
        </p>
      )}

      {estimate && (
        <dl className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Stat label="Source" value={estimate.source} />
          <Stat
            label="Drift (px/frame)"
            value={`${estimate.dxPerFrame.toFixed(2)}×${estimate.dyPerFrame.toFixed(2)}`}
          />
          <Stat
            label="Frames analyzed"
            value={estimate.framesAnalyzed.toLocaleString()}
          />
          <Stat
            label="Compensation"
            value={estimate.compensationApplied ? 'Applied' : 'None'}
          />
        </dl>
      )}
    </div>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-surface-800 bg-surface-900/60 px-3 py-2">
      <dt className="text-xs text-surface-500">{label}</dt>
      <dd className="mt-0.5 font-mono text-sm text-surface-200">{value}</dd>
    </div>
  )
}