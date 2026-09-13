import { useMemo, useState } from 'react'
import type { CrossVideoProjectionPoint, Video } from '@orchardvision/types'
import type { ProjectionMethod } from '../../api/videos'
import { useCrossVideoProjection } from '../../hooks/useVideos'
import { BboxThumbnail } from './BboxThumbnail'

const VIEW = 200
const PAD = 12
const PROJECTION_METHODS: ProjectionMethod[] = ['tsne', 'pca', 'umap']

function toViewport(value: number): number {
  const normalized = Math.max(-1, Math.min(1, value))
  return PAD + ((normalized + 1) / 2) * (VIEW - 2 * PAD)
}

const VIDEO_PALETTE = [
  '#f59e0b',
  '#22d3ee',
  '#a78bfa',
  '#34d399',
  '#fb7185',
  '#60a5fa',
  '#facc15',
  '#f472b6',
  '#4ade80',
  '#fb923c',
]

interface CrossVideoMapProps {
  videos: Video[]
  enabled: boolean
}

export function CrossVideoMap({ videos, enabled }: CrossVideoMapProps) {
  const [method, setMethod] = useState<ProjectionMethod>('tsne')
  const [selected, setSelected] = useState<CrossVideoProjectionPoint | null>(null)
  const { data, isLoading, isError } = useCrossVideoProjection(method, enabled)

  const points = useMemo(() => data?.points ?? [], [data])
  const videoIndex = useMemo(() => new Map(videos.map((v, i) => [v.id, i])), [videos])
  const videoName = useMemo(() => new Map(videos.map((v) => [v.id, v.originalName])), [videos])

  if (!enabled) return null

  if (isLoading) {
    return (
      <div className="flex h-40 items-center justify-center rounded-xl border border-surface-800 bg-surface-950">
        <span className="text-sm text-surface-500">Projecting cross-video embeddings…</span>
      </div>
    )
  }

  if (isError) {
    return (
      <div className="rounded-xl border border-surface-800 bg-surface-950 p-5 text-sm text-red-400">
        Failed to load cross-video embedding projection.
      </div>
    )
  }

  if (points.length === 0) {
    return (
      <div className="flex h-40 items-center justify-center rounded-xl border border-surface-800 bg-surface-950">
        <p className="text-sm text-surface-500">
          Process at least one video to project embeddings across videos.
        </p>
      </div>
    )
  }

  return (
    <div className="rounded-xl border border-surface-800 bg-surface-950">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-surface-800 px-4 py-3">
        <div>
          <h3 className="font-medium text-surface-200">Embedding map · cross-video</h3>
          <p className="text-xs text-surface-500">
            {data?.method.toUpperCase()} projection · {points.length} observations ·{' '}
            {data?.videoCount ?? 0} videos
          </p>
        </div>
        <div className="flex gap-1" role="tablist" aria-label="Projection method">
          {PROJECTION_METHODS.map((candidate) => (
            <button
              key={candidate}
              type="button"
              role="tab"
              aria-selected={method === candidate}
              onClick={() => setMethod(candidate)}
              className={`rounded-md border px-2.5 py-1 text-xs transition-colors ${
                method === candidate
                  ? 'border-surface-600 bg-surface-800 text-surface-100'
                  : 'border-surface-700 text-surface-400 hover:bg-surface-800 hover:text-surface-200'
              }`}
            >
              {candidate.toUpperCase()}
            </button>
          ))}
        </div>
      </div>
      <div className="p-3">
        <svg
          viewBox={`0 0 ${VIEW} ${VIEW}`}
          role="img"
          aria-label="Cross-video embedding projection scatter plot"
          className="h-96 w-full rounded-lg bg-surface-900"
        >
          {Array.from({ length: 5 }, (_, i) => {
            const pos = PAD + (i * (VIEW - 2 * PAD)) / 4
            return (
              <g key={i}>
                <line x1={pos} y1={PAD} x2={pos} y2={VIEW - PAD} className="stroke-surface-800" />
                <line x1={PAD} y1={pos} x2={VIEW - PAD} y2={pos} className="stroke-surface-800" />
              </g>
            )
          })}
          {points.map((point) => {
            const cx = toViewport(point.x)
            const cy = toViewport(point.y)
            const fill = VIDEO_PALETTE[(videoIndex.get(point.videoId) ?? 0) % VIDEO_PALETTE.length]
            return (
              <circle
                key={`${point.videoId}-${point.identityId}-${point.frameId}-${point.trackId ?? 'n'}`}
                cx={cx}
                cy={cy}
                r={4}
                fill={fill}
                fillOpacity={point.isOccluded ? 0.45 : 0.9}
                stroke={fill}
                strokeWidth={1.5}
                strokeOpacity={0.4}
                className="cursor-pointer"
                data-testid={`cross-video-point-${point.videoId}-${point.identityId}-${point.frameId}`}
                onClick={() => setSelected(point)}
                onMouseEnter={() => setSelected(point)}
                onMouseLeave={() => setSelected(null)}
              >
                <title>{`${videoName.get(point.videoId) ?? point.videoId} · id-${point.identityId} · f${point.frameId}`}</title>
              </circle>
            )
          })}
        </svg>
        <div className="mt-3 flex flex-wrap gap-3">
          {videos.map((video, i) => (
            <span key={video.id} className="flex items-center gap-1.5 text-xs text-surface-400">
              <span
                className="inline-block h-2.5 w-2.5 rounded-full"
                style={{ backgroundColor: VIDEO_PALETTE[i % VIDEO_PALETTE.length] }}
              />
              {video.originalName}
            </span>
          ))}
        </div>
        <div className="mt-3 flex h-32 items-center">
          {selected && (
            <div
              role="status"
              className="flex w-full items-center gap-3 rounded-lg border border-surface-800 bg-surface-900/60 p-2"
            >
              <BboxThumbnail
                videoId={selected.videoId}
                frameId={selected.frameId}
                bbox={selected.bbox}
                videoWidth={videos.find((v) => v.id === selected.videoId)?.width ?? null}
                videoHeight={videos.find((v) => v.id === selected.videoId)?.height ?? null}
              />
              <div className="flex min-w-0 flex-1 flex-col gap-1.5">
                <p className="font-mono text-xs text-surface-300">
                  {videoName.get(selected.videoId) ?? selected.videoId} · id-{selected.identityId} ·
                  f{selected.frameId} · track {selected.trackId ?? '—'}
                </p>
                <p className="font-mono text-xs text-surface-400">
                  conf {selected.confidence.toFixed(2)}
                  {selected.isOccluded ? ' · occluded' : ''}
                </p>
                {selected.qualityScore !== null && (
                  <p className="font-mono text-xs text-surface-400">
                    proto sim {selected.qualityScore.toFixed(3)}
                  </p>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
