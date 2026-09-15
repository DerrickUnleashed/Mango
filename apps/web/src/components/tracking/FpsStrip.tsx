import type { FrameTiming } from '@orchardvision/types'

const TARGET_BARS = 240

function downsample(timings: FrameTiming[], target: number): FrameTiming[] {
  if (timings.length <= target) return timings
  const bucket = Math.ceil(timings.length / target)
  const out: FrameTiming[] = []
  for (let i = 0; i < timings.length; i += bucket) {
    const chunk = timings.slice(i, i + bucket)
    out.push({
      ...chunk[chunk.length - 1],
      elapsedMs: chunk.reduce((sum, t) => sum + t.elapsedMs, 0) / chunk.length,
      fps: chunk.reduce((sum, t) => sum + t.fps, 0) / chunk.length,
    })
  }
  return out
}

function colorFor(fps: number, maxFps: number): string {
  const ratio = maxFps > 0 ? fps / maxFps : 0
  const hue = 120 * Math.max(0.05, Math.min(1, ratio))
  return `hsl(${hue} 60% 45%)`
}

function formatFps(fps: number): string {
  return Number.isFinite(fps) ? fps.toFixed(0) : '—'
}

export function FpsStrip({ timings }: { timings: FrameTiming[] }) {
  if (timings.length === 0) {
    return <p className="text-xs text-surface-500">No per-frame timing data — run processing.</p>
  }

  const maxFps = Math.max(...timings.map((t) => t.fps))
  const avgFps = timings.reduce((sum, t) => sum + t.fps, 0) / timings.length
  const bars = downsample(timings, TARGET_BARS)

  return (
    <div className="glass-soft rounded-lg p-4">
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-sm font-medium text-surface-300">Processing speed per frame</h3>
        <span className="font-mono text-xs text-surface-400">
          {timings.length} frames · avg {formatFps(avgFps)} fps
        </span>
      </div>
      <div
        className="mt-3 flex h-20 items-end gap-px"
        role="img"
        aria-label="Per-frame processing speed strip chart"
      >
        {bars.map((timing) => (
          <div
            key={timing.frameId}
            className="flex-1 rounded-sm"
            style={{
              height: `${Math.max(4, (timing.fps / Math.max(maxFps, 1)) * 100)}%`,
              backgroundColor: colorFor(timing.fps, maxFps),
            }}
            title={`frame ${timing.frameId}: ${formatFps(timing.fps)} fps (${timing.elapsedMs.toFixed(1)} ms)`}
          />
        ))}
      </div>
    </div>
  )
}
