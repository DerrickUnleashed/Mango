import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  createExperiment,
  deleteExperiment,
  getExperiments,
} from '../api/experiments'
import type { Experiment, ExperimentMetrics } from '@orchardvision/types'

const METRIC_ROWS: { key: keyof ExperimentMetrics; label: string; digits: number }[] = [
  { key: 'idf1', label: 'IDF1', digits: 3 },
  { key: 'hota', label: 'HOTA', digits: 3 },
  { key: 'identityRecoveryRate', label: 'Re-ID recovery', digits: 3 },
  { key: 'countMae', label: 'Count MAE', digits: 3 },
  { key: 'countMape', label: 'Count MAPE', digits: 1 },
  { key: 'idSwitches', label: 'ID switches', digits: 0 },
  { key: 'trackFragmentation', label: 'Fragmentation', digits: 3 },
]

const TREND_METRICS: { key: keyof ExperimentMetrics; label: string; higherIsBetter: boolean }[] = [
  { key: 'idf1', label: 'IDF1', higherIsBetter: true },
  { key: 'hota', label: 'HOTA', higherIsBetter: true },
  { key: 'identityRecoveryRate', label: 'Re-ID recovery', higherIsBetter: true },
  { key: 'countMape', label: 'Count MAPE', higherIsBetter: false },
  { key: 'trackFragmentation', label: 'Fragmentation', higherIsBetter: false },
]

export function ExperimentsPage() {
  const queryClient = useQueryClient()
  const { data, isLoading } = useQuery({
    queryKey: ['experiments'],
    queryFn: getExperiments,
  })
  const experiments = data?.experiments ?? []
  const isRunning = experiments.some((e) => e.status === 'running')

  const createMutation = useMutation({
    mutationFn: createExperiment,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['experiments'] })
    },
  })
  const deleteMutation = useMutation({
    mutationFn: deleteExperiment,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['experiments'] })
    },
  })

  const [tracker, setTracker] = useState<'mock' | 'bytetrack'>('mock')
  const [frames, setFrames] = useState(310)
  const [error, setError] = useState<string | null>(null)
  const [confirmingId, setConfirmingId] = useState<string | null>(null)

  async function handleRun() {
    setError(null)
    try {
      await createMutation.mutateAsync({ tracker, num_frames: frames })
    } catch {
      setError('Failed to start experiment.')
    }
  }

  async function handleDelete(id: string) {
    setConfirmingId(null)
    try {
      await deleteMutation.mutateAsync(id)
    } catch {
      setError('Failed to delete experiment.')
    }
  }

  const baseline = baselineByTracker(experiments)
  const trends = trendRuns(experiments)

  return (
    <div className="mx-auto max-w-7xl">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-surface-50">Experiments</h1>
          <p className="mt-1 text-sm text-surface-400">
            Run the orchard scenario with different trackers to study identity recovery under
            occlusion and camera motion.
          </p>
        </div>
      </div>

      <div className="mt-6 rounded-xl border border-surface-800 bg-surface-950 p-5">
        <div className="flex flex-wrap items-end gap-4">
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-surface-400">Tracker</span>
            <select
              value={tracker}
              onChange={(e) => setTracker(e.target.value as 'mock' | 'bytetrack')}
              className="rounded-lg border border-surface-700 bg-surface-900 px-3 py-2 text-surface-100"
            >
              <option value="mock">Mock (identity primitives)</option>
              <option value="bytetrack">ByteTrack baseline</option>
            </select>
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-surface-400">Scenario frames</span>
            <input
              type="number"
              min={10}
              max={1000}
              value={frames}
              onChange={(e) => setFrames(Number(e.target.value))}
              className="w-32 rounded-lg border border-surface-700 bg-surface-900 px-3 py-2 text-surface-100"
            />
          </label>
          <button
            onClick={handleRun}
            disabled={createMutation.isPending || isRunning}
            className="rounded-lg bg-orchard-500 px-4 py-2 text-sm font-medium text-surface-950 hover:bg-orchard-400 disabled:opacity-50"
          >
            {createMutation.isPending ? 'Running…' : 'Run experiment'}
          </button>
          {isRunning && (
            <span className="text-xs text-amber-300">
              One experiment is still running on the server.
            </span>
          )}
        </div>
        {error && <p className="mt-3 text-sm text-red-400">{error}</p>}
      </div>

      {baseline.length > 1 && (
        <div className="mt-6 rounded-xl border border-surface-800 bg-surface-950 p-5">
          <h2 className="font-medium text-surface-200">Tracker baseline comparison</h2>
          <p className="mt-1 text-sm text-surface-400">
            Medians across completed runs per tracker.
          </p>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-surface-800 text-left text-xs text-surface-500">
                  <th className="py-2 pr-4 font-medium">Tracker</th>
                  {METRIC_ROWS.map((row) => (
                    <th key={row.key} className="py-2 pr-4 text-right font-medium">
                      {row.label}
                    </th>
                  ))}
                  <th className="py-2 pr-4 text-right font-medium">Runs</th>
                </tr>
              </thead>
              <tbody>
                {baseline.map((row) => (
                  <tr key={row.tracker} className="border-b border-surface-800/50">
                    <td className="py-2 pr-4 font-medium text-surface-200">{row.tracker}</td>
                    {METRIC_ROWS.map((metric) => (
                      <td key={metric.key} className="py-2 pr-4 text-right font-mono text-surface-300">
                        {row.metrics[metric.key] !== null
                          ? row.metrics[metric.key]!.toFixed(metric.digits)
                          : '—'}
                      </td>
                    ))}
                    <td className="py-2 pr-4 text-right text-surface-400">{row.runs}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {trends.length > 0 && (
        <div className="mt-6 rounded-xl border border-surface-800 bg-surface-950 p-5">
          <h2 className="font-medium text-surface-200">Metric trends over runs</h2>
          <p className="mt-1 text-sm text-surface-400">
            Completed runs in creation order; cyan = mock tracker, amber = bytetrack.
          </p>
          <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {TREND_METRICS.map((metric) => (
              <TrendChart
                key={metric.key}
                metric={metric}
                runs={trends}
                digits={metric.key === 'countMape' ? 1 : 3}
              />
            ))}
          </div>
        </div>
      )}

      <div className="mt-6 space-y-3">
        {experiments.length === 0 && !isLoading && (
          <p className="rounded-lg border border-dashed border-surface-800 px-4 py-8 text-center text-sm text-surface-500">
            No experiments yet — pick a tracker above and run one.
          </p>
        )}
        {isLoading && <p className="px-4 py-8 text-center text-sm text-surface-500">Loading experiments…</p>}
        {experiments.map((experiment) => (
          <ExperimentRow
            key={experiment.id}
            experiment={experiment}
            confirming={confirmingId === experiment.id}
            onAskDelete={() => setConfirmingId(experiment.id)}
            onCancelDelete={() => setConfirmingId(null)}
            onDelete={() => handleDelete(experiment.id)}
          />
        ))}
      </div>
    </div>
  )
}

function ExperimentRow({
  experiment,
  confirming,
  onAskDelete,
  onCancelDelete,
  onDelete,
}: {
  experiment: Experiment
  confirming: boolean
  onAskDelete: () => void
  onCancelDelete: () => void
  onDelete: () => void
}) {
  return (
    <div className="rounded-xl border border-surface-800 bg-surface-950 p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="font-medium text-surface-200">{experiment.name}</h3>
            <StatusBadge status={experiment.status} />
          </div>
          <p className="mt-1 text-xs text-surface-500">
            {experiment.tracker} · {experiment.scenario} · {experiment.numFrames} frames
            {experiment.createdAt
              ? ` · started ${new Date(experiment.createdAt).toLocaleString()}`
              : ''}
          </p>
        </div>
        {confirming ? (
          <div className="flex items-center gap-2">
            <span className="text-xs text-surface-400">Delete this run?</span>
            <button
              onClick={onDelete}
              className="rounded-lg bg-red-500/15 px-3 py-1.5 text-xs font-medium text-red-300 hover:bg-red-500/25"
            >
              Delete
            </button>
            <button
              onClick={onCancelDelete}
              className="rounded-lg border border-surface-700 px-3 py-1.5 text-xs text-surface-300"
            >
              Cancel
            </button>
          </div>
        ) : (
          <button
            onClick={onAskDelete}
            className="rounded-lg border border-surface-700 px-3 py-1.5 text-xs text-surface-400 hover:text-surface-200"
          >
            Delete
          </button>
        )}
      </div>

      {experiment.status === 'completed' && experiment.metrics && (
        <dl className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
          {METRIC_ROWS.map((row) => (
            <div key={row.key} className="rounded-lg border border-surface-800 bg-surface-900/60 px-3 py-2">
              <dt className="text-xs text-surface-500">{row.label}</dt>
              <dd className="mt-0.5 font-mono text-sm text-surface-200">
                {experiment.metrics![row.key].toFixed(row.digits)}
              </dd>
            </div>
          ))}
        </dl>
      )}
      {experiment.status === 'failed' && (
        <p className="mt-3 text-sm text-red-400">{experiment.error ?? 'Experiment failed.'}</p>
      )}
      {experiment.status === 'running' && (
        <p className="mt-3 text-sm text-amber-300">Running…</p>
      )}
    </div>
  )
}

function StatusBadge({ status }: { status: Experiment['status'] }) {
  const styles: Record<Experiment['status'], string> = {
    running: 'bg-amber-500/15 text-amber-300',
    completed: 'bg-emerald-500/15 text-emerald-300',
    failed: 'bg-red-500/15 text-red-300',
  }
  return (
    <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${styles[status]}`}>
      {status}
    </span>
  )
}

function baselineByTracker(
  experiments: Experiment[],
): { tracker: string; metrics: Partial<Record<keyof ExperimentMetrics, number>>; runs: number }[] {
  const groups: Record<string, ExperimentMetrics[]> = {}
  for (const experiment of experiments) {
    if (experiment.status === 'completed' && experiment.metrics) {
      groups[experiment.tracker] = [...(groups[experiment.tracker] ?? []), experiment.metrics]
    }
  }
  return Object.entries(groups).map(([tracker, rows]) => {
    const metrics: Partial<Record<keyof ExperimentMetrics, number>> = {}
    for (const row of METRIC_ROWS) {
      metrics[row.key] = median(rows.map((r) => r[row.key]))
    }
    return { tracker, metrics, runs: rows.length }
  })
}

function median(values: number[]): number {
  if (values.length === 0) return 0
  const sorted = [...values].sort((a, b) => a - b)
  const mid = Math.floor(sorted.length / 2)
  return sorted.length % 2 === 0 ? (sorted[mid - 1] + sorted[mid]) / 2 : sorted[mid]
}

function trendRuns(
  experiments: Experiment[],
): { tracker: Experiment['tracker']; values: Partial<Record<keyof ExperimentMetrics, number>> }[] {
  return [...experiments]
    .sort((a, b) => (a.createdAt ?? '').localeCompare(b.createdAt ?? ''))
    .filter((e) => e.status === 'completed' && e.metrics)
    .map((e) => ({ tracker: e.tracker, values: e.metrics! }))
}

function TrendChart({
  metric,
  runs,
  digits,
}: {
  metric: (typeof TREND_METRICS)[number]
  runs: ReturnType<typeof trendRuns>
  digits: number
}) {
  const WIDTH = 240
  const HEIGHT = 80
  const PAD = 6
  const points = runs
    .map((run, index) => ({ ...run, index, value: run.values[metric.key] }))
    .filter((p): p is (typeof p) & { value: number } => typeof p.value === 'number')
  if (points.length === 0) {
    return (
      <div className="rounded-lg border border-surface-800 bg-surface-900/60 p-4">
        <h3 className="text-sm font-medium text-surface-300">{metric.label}</h3>
        <p className="mt-3 text-xs text-surface-500">No completed runs yet.</p>
      </div>
    )
  }
  const values = points.map((p) => p.value)
  const min = Math.min(...values)
  const max = Math.max(...values)
  const span = max - min || 1
  const x = (index: number) => PAD + write((index / Math.max(1, points.length - 1)) * (WIDTH - 2 * PAD))
  const y = (value: number) => HEIGHT - PAD - ((value - min) / span) * (HEIGHT - 2 * PAD)
  const series = (tracker: Experiment['tracker']) =>
    points.filter((p) => p.tracker === tracker).map((p) => `${x(p.index)},${y(p.value)}`).join(' ')
  return (
    <div className="rounded-lg border border-surface-800 bg-surface-900/60 p-4">
      <h3 className="text-sm font-medium text-surface-300">{metric.label}</h3>
      <svg
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        className="mt-2 h-20 w-full"
        role="img"
        aria-label={`${metric.label} across runs`}
      >
        <polyline
          points={series('mock')}
          fill="none"
          stroke="#22d3ee"
          strokeWidth={1.5}
          strokeLinejoin="round"
        />
        <polyline
          points={series('bytetrack')}
          fill="none"
          stroke="#fbbf24"
          strokeWidth={1.5}
          strokeLinejoin="round"
        />
        {points.map((p) => (
          <circle key={`${p.tracker}-${p.index}`} cx={x(p.index)} cy={y(p.value)} r={2.5} fill={p.tracker === 'mock' ? '#22d3ee' : '#fbbf24'} />
        ))}
      </svg>
      <p className="mt-2 text-[11px] text-surface-500">
        range {min.toFixed(digits)} – {max.toFixed(digits)} · {metric.higherIsBetter ? 'higher is better' : 'lower is better'}
      </p>
    </div>
  )
}

// write() is a small alias to keep `Math.round` semantics in one place.
function write(value: number): number {
  return Math.round(value * 100) / 100
}