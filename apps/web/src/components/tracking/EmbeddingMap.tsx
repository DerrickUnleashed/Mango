import { useMemo, useState } from 'react'
import type { IdentityProjectionPoint } from '@orchardvision/types'
import { useIdentityProjection } from '../../hooks/useVideos'

export const EMBEDDING_PALETTE = [
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

export function colorForIdentity(identityId: number): string {
  return EMBEDDING_PALETTE[identityId % EMBEDDING_PALETTE.length]
}

const VIEW = 200
const PAD = 12

function toViewport(value: number): number {
  const normalized = Math.max(-1, Math.min(1, value))
  return PAD + ((normalized + 1) / 2) * (VIEW - 2 * PAD)
}

function radiusFor(point: IdentityProjectionPoint): number {
  return 4 + Math.min(9, Math.log10(point.observationCount + 1) * 5)
}

interface EmbeddingMapProps {
  videoId: string
  enabled: boolean
}

export function EmbeddingMap({ videoId, enabled }: EmbeddingMapProps) {
  const [overlay, setOverlay] = useState<IdentityProjectionPoint | null>(null)
  const { data, isLoading, isError } = useIdentityProjection(videoId, enabled)

  const points = useMemo(() => data?.points ?? [], [data])

  if (!enabled) return null

  if (isLoading) {
    return (
      <div className="flex h-40 items-center justify-center glass card-glow rounded-2xl">
        <span className="text-sm text-surface-500">Projecting embeddings…</span>
      </div>
    )
  }

  if (isError) {
    return (
      <div className="glass card-glow rounded-2xl p-5 text-sm text-red-400">
        Failed to load embedding projection.
      </div>
    )
  }

  if (points.length === 0) {
    return (
      <div className="flex h-40 items-center justify-center glass card-glow rounded-2xl">
        <p className="text-sm text-surface-500">Run processing to project identity embeddings.</p>
      </div>
    )
  }

  return (
    <div className="glass card-glow rounded-2xl">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-surface-800 px-4 py-3">
        <div>
          <h3 className="font-medium text-surface-200">Embedding map</h3>
          <p className="text-xs text-surface-500">
            {data?.method.toUpperCase()} projection · {points.length} identities
          </p>
        </div>
      </div>
      <div className="p-3">
        <svg
          viewBox={`0 0 ${VIEW} ${VIEW}`}
          role="img"
          aria-label="Identity embedding projection scatter plot"
          className="h-64 w-full rounded-lg bg-surface-900"
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
            const fill = colorForIdentity(point.identityId)
            return (
              <circle
                key={point.identityId}
                cx={cx}
                cy={cy}
                r={radiusFor(point)}
                fill={fill}
                fillOpacity={point.isConfident ? 0.95 : 0.55}
                stroke={fill}
                strokeWidth={1.5}
                strokeOpacity={0.4}
                className="cursor-pointer"
                data-testid={`embedding-point-${point.identityId}`}
                onMouseEnter={() => setOverlay(point)}
                onMouseLeave={() => setOverlay(null)}
              >
                <title>{`Identity ${point.identityId} · ${point.observationCount} obs · q ${point.quality.toFixed(2)}`}</title>
              </circle>
            )
          })}
        </svg>
        {overlay && (
          <p className="mt-2 text-center font-mono text-xs text-surface-400" role="status">
            id-{overlay.identityId} · {overlay.observationCount} obs · q{' '}
            {overlay.quality.toFixed(2)}
          </p>
        )}
      </div>
    </div>
  )
}
