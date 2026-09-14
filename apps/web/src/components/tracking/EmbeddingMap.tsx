import { useMemo, useState } from 'react'
import type { IdentityProjectionPoint, ObservationProjectionPoint } from '@orchardvision/types'
import type { ProjectionMethod } from '../../api/videos'
import { useIdentityProjection, useObservationProjection, useVideo } from '../../hooks/useVideos'
import { BboxThumbnail } from './BboxThumbnail'

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
const PROJECTION_METHODS: ProjectionMethod[] = ['tsne', 'pca', 'umap']

function toViewport(value: number): number {
  const normalized = Math.max(-1, Math.min(1, value))
  return PAD + ((normalized + 1) / 2) * (VIEW - 2 * PAD)
}

interface EmbeddingMapProps {
  videoId: string
  enabled: boolean
  variant?: 'compact' | 'full'
  onSeekFrame?: (frameId: number) => void
  onOpenIdentity?: (identityId: number) => void
}

export function EmbeddingMap({
  videoId,
  enabled,
  variant = 'compact',
  onSeekFrame,
  onOpenIdentity,
}: EmbeddingMapProps) {
  const [method, setMethod] = useState<ProjectionMethod>('tsne')
  const [selected, setSelected] = useState<ObservationProjectionPoint | null>(null)
  const [hoveredPrototype, setHoveredPrototype] = useState<IdentityProjectionPoint | null>(null)
  const [showPrototypes, setShowPrototypes] = useState(false)
  const { data, isLoading, isError } = useObservationProjection(videoId, method, enabled)
  const { data: prototypeData } = useIdentityProjection(videoId, method, enabled && showPrototypes)
  const video = useVideo(videoId)

  const points = useMemo(() => data?.points ?? [], [data])
  const prototypes = useMemo(
    () => (showPrototypes ? (prototypeData?.points ?? []) : []),
    [showPrototypes, prototypeData],
  )
  const full = variant === 'full'

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

  function handlePointClick(point: ObservationProjectionPoint) {
    setSelected(point)
    onSeekFrame?.(point.frameId)
    onOpenIdentity?.(point.identityId)
  }

  return (
    <div className="glass card-glow rounded-2xl">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-surface-800 px-4 py-3">
        <div>
          <h3 className="font-medium text-surface-200">Embedding map</h3>
          <p className="text-xs text-surface-500">
            {data?.method.toUpperCase()} projection · {points.length} observations
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <label className="flex cursor-pointer items-center gap-1.5 text-xs text-surface-400">
            <input
              type="checkbox"
              checked={showPrototypes}
              onChange={(e) => {
                setShowPrototypes(e.target.checked)
                setHoveredPrototype(null)
              }}
              className="h-3.5 w-3.5 accent-orchard-500"
            />
            Identity centroids
          </label>
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
      </div>
      <div className="p-3">
        <svg
          viewBox={`0 0 ${VIEW} ${VIEW}`}
          role="img"
          aria-label="Embedding projection scatter plot"
          className={`w-full rounded-lg bg-surface-900 ${full ? 'h-96' : 'h-64'}`}
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
            const active =
              selected !== null &&
              selected.identityId === point.identityId &&
              selected.frameId === point.frameId
            return (
              <circle
                key={`${point.identityId}-${point.frameId}-${point.trackId ?? 'n'}`}
                cx={cx}
                cy={cy}
                r={active ? 6 : 4}
                fill={fill}
                fillOpacity={point.isOccluded ? 0.45 : 0.9}
                stroke={fill}
                strokeWidth={1.5}
                strokeOpacity={0.4}
                className="cursor-pointer"
                data-testid={`embedding-point-${point.identityId}-${point.frameId}`}
                onClick={() => handlePointClick(point)}
                onMouseEnter={() => setSelected(point)}
                onMouseLeave={() => setSelected(null)}
              >
                <title>{`Identity ${point.identityId} · frame ${point.frameId} · conf ${point.confidence.toFixed(2)}`}</title>
              </circle>
            )
          })}
          {prototypes.map((prototype) => {
            const cx = toViewport(prototype.x)
            const cy = toViewport(prototype.y)
            return (
              <circle
                key={`prototype-${prototype.identityId}`}
                cx={cx}
                cy={cy}
                r={7}
                fill="none"
                stroke="#f1f5f9"
                strokeWidth={2}
                className="cursor-help"
                data-testid={`embedding-prototype-${prototype.identityId}`}
                onMouseEnter={() => setHoveredPrototype(prototype)}
                onMouseLeave={() => setHoveredPrototype(null)}
              >
                <title>{`Identity ${prototype.identityId} prototype · q ${prototype.quality.toFixed(2)}`}</title>
              </circle>
            )
          })}
        </svg>
        <div className="mt-3 flex h-32 items-center">
          {hoveredPrototype && (
            <div
              role="status"
              className="flex w-full items-center gap-3 rounded-lg border border-surface-800 bg-surface-900/60 p-2"
            >
              <span
                className="flex h-28 w-28 flex-col items-center justify-center rounded-md border border-surface-700 bg-surface-800 text-center"
                aria-label={`Identity ${hoveredPrototype.identityId} centroid`}
                role="img"
              >
                <span className="text-xl" aria-hidden="true">
                  ◯
                </span>
              </span>
              <div className="flex min-w-0 flex-1 flex-col gap-1.5">
                <p className="font-mono text-xs text-surface-300">
                  id-{hoveredPrototype.identityId} · prototype centroid
                </p>
                <p className="font-mono text-xs text-surface-400">
                  q {hoveredPrototype.quality.toFixed(2)} · {hoveredPrototype.observationCount} obs
                  {hoveredPrototype.isConfident ? ' · confident' : ''}
                </p>
              </div>
            </div>
          )}
          {!hoveredPrototype && selected && (
            <div
              role="status"
              className="flex w-full items-center gap-3 rounded-lg border border-surface-800 bg-surface-900/60 p-2"
            >
              <BboxThumbnail
                videoId={videoId}
                frameId={selected.frameId}
                bbox={selected.bbox}
                videoWidth={video.data?.width ?? null}
                videoHeight={video.data?.height ?? null}
              />
              <div className="flex min-w-0 flex-1 flex-col gap-1.5">
                <p className="font-mono text-xs text-surface-300">
                  id-{selected.identityId} · f{selected.frameId} · track {selected.trackId ?? '—'}
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
                {(onSeekFrame || onOpenIdentity) && (
                  <div className="flex gap-2 pt-0.5">
                    {onSeekFrame && (
                      <button
                        type="button"
                        onClick={() => onSeekFrame(selected.frameId)}
                        className="rounded-md border border-surface-700 px-2 py-1 text-xs text-surface-300 transition-colors hover:bg-surface-800 hover:text-surface-100"
                      >
                        Seek frame
                      </button>
                    )}
                    {onOpenIdentity && (
                      <button
                        type="button"
                        onClick={() => onOpenIdentity(selected.identityId)}
                        className="rounded-md border border-surface-700 px-2 py-1 text-xs text-surface-300 transition-colors hover:bg-surface-800 hover:text-surface-100"
                      >
                        View identity
                      </button>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
