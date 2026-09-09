import { useAnalytics } from '../../hooks/useVideos'

interface AnalyticsPanelProps {
  videoId: string
  enabled: boolean
}

export function AnalyticsPanel({ videoId, enabled }: AnalyticsPanelProps) {
  const { data: summary, isLoading, isError } = useAnalytics(videoId, enabled)

  if (!enabled) return null

  return (
    <div className="rounded-xl border border-surface-800 bg-surface-950 p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="font-medium text-surface-200">Analytics</h2>
          <p className="mt-1 text-sm text-surface-400">
            Aggregates over the whole processing run: detections, tracks, identities, and
            recoveries.
          </p>
        </div>
        {summary && (
          <span className="rounded-full bg-orchard-500/15 px-2.5 py-1 text-xs font-medium text-orchard-300">
            {summary.totalFrames.toLocaleString()} frames
          </span>
        )}
      </div>

      {isLoading && <p className="mt-4 text-sm text-surface-500">Loading analytics…</p>}
      {isError && (
        <p className="mt-4 text-sm text-red-400">Failed to load video analytics.</p>
      )}
      {!isLoading && !isError && summary === null && (
        <p className="mt-4 text-sm text-surface-500">
          No analytics yet — run processing to aggregate results.
        </p>
      )}

      {summary && (
        <>
          <dl className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
            <Stat label="Total detections" value={summary.totalFruitDetections.toLocaleString()} />
            <Stat label="Unique identities" value={summary.uniqueIdentities.toLocaleString()} />
            <Stat label="Active tracks" value={summary.activeTracks.toLocaleString()} />
            <Stat label="Lost tracks" value={summary.lostTracks.toLocaleString()} />
            <Stat label="Re-identified" value={summary.recoveredIdentities.toLocaleString()} />
            <Stat label="Avg confidence" value={summary.avgConfidence.toFixed(2)} />
          </dl>

          <div className="mt-5 grid gap-5 lg:grid-cols-2">
            <SeriesChart
              title="Fruits detected per frame"
              data={summary.fruitPerFrame}
              color="#f59e0b"
            />
            <SeriesChart
              title="Active tracks per frame"
              data={summary.tracksPerFrame}
              color="#22d3ee"
            />
            <SeriesChart
              title="Track losses per frame"
              data={summary.lossesPerFrame}
              color="#fb7185"
            />
            <DistributionChart
              title="Confidence distribution"
              data={summary.confidenceDistribution}
              color="#34d399"
            />
          </div>

          <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Stat label="Occlusion events" value={summary.occlusionEvents.toLocaleString()} />
            <Stat
              label="Avg tracking FPS"
              value={summary.avgTrackingFps > 0 ? summary.avgTrackingFps.toFixed(0) : '—'}
            />
            <Stat
              label="Processing time"
              value={
                summary.processingSeconds > 0
                  ? `${summary.processingSeconds.toFixed(1)}s`
                  : '—'
              }
            />
            <Stat label="Occlusion run types" value={summary.occlusionDurationDistribution.length.toString()} />
          </div>
        </>
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

interface SeriesPoint {
  frameId: number
  count: number
}

function SeriesChart({
  title,
  data,
  color,
}: {
  title: string
  data: SeriesPoint[]
  color: string
}) {
  const max = Math.max(1, ...data.map((d) => d.count))
  const points = data.length > 240 ? downsample(data, 240) : data
  return (
    <div className="rounded-lg border border-surface-800 bg-surface-900/60 p-4">
      <h3 className="text-sm font-medium text-surface-300">{title}</h3>
      <div className="mt-3 flex h-24 items-end gap-px">
        {points.map((point) => (
          <div
            key={point.frameId}
            className="flex-1 rounded-sm"
            style={{
              height: `${Math.max(4, (point.count / max) * 100)}%`,
              backgroundColor: color,
              opacity: 0.7 + 0.3 * (point.count / max),
            }}
            title={`frame ${point.frameId}: ${point.count}`}
          />
        ))}
      </div>
    </div>
  )
}

interface DistributionBin {
  label: string
  count: number
}

function DistributionChart({
  title,
  data,
  color,
}: {
  title: string
  data: DistributionBin[]
  color: string
}) {
  const max = Math.max(1, ...data.map((d) => d.count))
  return (
    <div className="rounded-lg border border-surface-800 bg-surface-900/60 p-4">
      <h3 className="text-sm font-medium text-surface-300">{title}</h3>
      <div className="mt-3 space-y-1.5">
        {data.map((bin) => (
          <div key={bin.label} className="flex items-center gap-2">
            <span className="w-14 flex-shrink-0 text-[11px] text-surface-500">{bin.label}</span>
            <div className="h-4 flex-1 overflow-hidden rounded bg-surface-800">
              <div
                className="h-full rounded"
                style={{ width: `${(bin.count / max) * 100}%`, backgroundColor: color }}
              />
            </div>
            <span className="w-10 flex-shrink-0 text-right font-mono text-[11px] text-surface-400">
              {bin.count}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

function downsample(points: SeriesPoint[], target: number): SeriesPoint[] {
  if (points.length <= target) return points
  const bucket = Math.ceil(points.length / target)
  const out: SeriesPoint[] = []
  for (let i = 0; i < points.length; i += bucket) {
    const chunk = points.slice(i, i + bucket)
    out.push({
      frameId: chunk[chunk.length - 1].frameId,
      count: chunk.reduce((sum, p) => sum + p.count, 0) / chunk.length,
    })
  }
  return out
}