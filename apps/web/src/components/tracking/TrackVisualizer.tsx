import { useEffect, useMemo, useRef, useState } from 'react'
import type { PersistedReidEvent, PersistedTrack } from '@orchardvision/types'
import { useFrameDetections, useReidEvents, useTracks } from '../../hooks/useVideos'

const PALETTE = [
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

function colorFor(trackId: number): string {
  return PALETTE[trackId % PALETTE.length]
}

function centerOf(bbox: number[]): [number, number] {
  const [x, y, w, h] = bbox
  return [x + w / 2, y + h / 2]
}

function drawMarker(ctx: CanvasRenderingContext2D, bbox: number[], color: string, glyph: string) {
  const [cx, cy] = centerOf(bbox)
  ctx.save()
  ctx.font = '14px ui-sans-serif, system-ui'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.fillStyle = color
  ctx.globalAlpha = 1
  ctx.strokeStyle = 'rgba(15, 23, 42, 0.9)'
  ctx.lineWidth = 3
  ctx.strokeText(glyph, cx, cy - 16)
  ctx.fillText(glyph, cx, cy - 16)
  ctx.restore()
}

function drawOcclusionBand(ctx: CanvasRenderingContext2D, bbox: number[]) {
  const [x, y, w, h] = bbox
  ctx.save()
  ctx.globalAlpha = 0.16
  ctx.fillStyle = '#f59e0b'
  ctx.fillRect(x, y, w, h)
  ctx.restore()
  ctx.save()
  ctx.setLineDash([4, 4])
  ctx.strokeStyle = 'rgba(251, 191, 36, 0.55)'
  ctx.lineWidth = 1
  ctx.strokeRect(x - 3, y - 3, w + 6, h + 6)
  ctx.restore()
}

interface TrackVisualizerProps {
  videoId: string
  width: number
  height: number
  frameCount: number
  enabled: boolean
}

export function TrackVisualizer({
  videoId,
  width,
  height,
  frameCount,
  enabled,
}: TrackVisualizerProps) {
  const { data, isLoading, isError } = useTracks(videoId, enabled)
  const { data: reidData } = useReidEvents(videoId, enabled)
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const tracks = useMemo(() => data?.tracks ?? [], [data])
  const events = useMemo(() => reidData?.events ?? [], [reidData])
  const maxFrame = Math.max(0, frameCount - 1)

  const [frame, setFrame] = useState(0)
  const [selected, setSelected] = useState<number | null>(null)
  const [showDetections, setShowDetections] = useState(true)
  const { data: detectionsData } = useFrameDetections(videoId, frame, enabled)
  const detections = useMemo(() => detectionsData?.detections ?? [], [detectionsData])

  const eventsByTrack = useMemo(() => {
    const map = new Map<number, PersistedReidEvent[]>()
    for (const event of events) {
      const list = map.get(event.trackId) ?? []
      list.push(event)
      map.set(event.trackId, list)
    }
    return map
  }, [events])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || !tracks.length) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    ctx.clearRect(0, 0, width, height)
    ctx.fillStyle = 'rgba(15, 23, 42, 0.25)'
    ctx.fillRect(0, 0, width, height)

    const pointAt = (track: PersistedTrack, targetFrame: number, edge: 'before' | 'after') => {
      const ordered = [...track.points].sort((a, b) => a.frameId - b.frameId)
      if (edge === 'before') {
        for (let i = ordered.length - 1; i >= 0; i -= 1) {
          if (ordered[i].frameId <= targetFrame) return ordered[i]
        }
      } else {
        for (const point of ordered) {
          if (point.frameId >= targetFrame) return point
        }
      }
      return null
    }

    for (const track of tracks) {
      const color = colorFor(track.trackId)
      const visible = track.points.filter((p) => p.frameId <= frame)

      if (visible.length >= 2) {
        ctx.beginPath()
        ctx.moveTo(
          visible[0].bbox[0] + visible[0].bbox[2] / 2,
          visible[0].bbox[1] + visible[0].bbox[3] / 2,
        )
        for (const p of visible.slice(1)) {
          ctx.lineTo(p.bbox[0] + p.bbox[2] / 2, p.bbox[1] + p.bbox[3] / 2)
        }
        ctx.strokeStyle = color
        ctx.globalAlpha = 0.6
        ctx.lineWidth = 1.5
        ctx.stroke()
        ctx.globalAlpha = 1
      }

      const current = track.points.filter((p) => p.frameId === frame)
      if (current.length === 1) {
        const p = current[0]
        const [x, y, w, h] = p.bbox
        ctx.beginPath()
        ctx.rect(x, y, w, h)
        ctx.strokeStyle = color
        ctx.lineWidth = 2
        ctx.stroke()
        ctx.fillStyle = color
        ctx.globalAlpha = 0.28
        ctx.fillRect(x, y, w, h)
        ctx.globalAlpha = 1
        ctx.font = '12px ui-sans-serif, system-ui'
        ctx.fillText(`#${track.trackId}`, x, Math.max(y - 4, 12))
      }

      const trackEvents = eventsByTrack.get(track.trackId) ?? []
      for (const event of trackEvents) {
        if (event.accepted && frame >= event.lostFrameId) {
          const lostPoint = pointAt(track, event.lostFrameId, 'before')
          const reappearPoint = pointAt(track, event.reappearanceFrameId, 'after')
          if (lostPoint) {
            drawMarker(
              ctx,
              lostPoint.bbox,
              event.lostFrameId === frame ? '#fb7185' : '#fb7185',
              '×',
            )
          }
          if (reappearPoint) {
            drawMarker(
              ctx,
              reappearPoint.bbox,
              event.reappearanceFrameId === frame ? '#34d399' : '#34d399',
              '✓',
            )
          }
          if (frame > event.lostFrameId && frame < event.reappearanceFrameId) {
            const gapPoint = pointAt(track, frame, 'before')
            if (gapPoint) drawOcclusionBand(ctx, gapPoint.bbox)
          }
        }
      }
    }

    if (showDetections) {
      for (const det of detections) {
        const [x, y, w, h] = det.bbox
        ctx.beginPath()
        ctx.rect(x, y, w, h)
        ctx.strokeStyle = '#e2e8f0'
        ctx.globalAlpha = 0.75
        ctx.setLineDash([4, 4])
        ctx.lineWidth = 1.25
        ctx.stroke()
        ctx.setLineDash([])
        ctx.globalAlpha = 1
        ctx.font = '10px ui-sans-serif, system-ui'
        ctx.fillStyle = 'rgba(226, 232, 240, 0.9)'
        ctx.fillText(
          `d${det.confidence.toFixed(2)}${det.isOccluded ? '·occ' : ''}`,
          x,
          Math.max(y + h + 11, 12),
        )
        if (det.isOccluded) {
          ctx.beginPath()
          ctx.rect(x - 2, y - 2, w + 4, h + 4)
          ctx.strokeStyle = 'rgba(251, 191, 36, 0.85)'
          ctx.setLineDash([3, 3])
          ctx.lineWidth = 1.5
          ctx.stroke()
          ctx.setLineDash([])
        }
      }
    }
  }, [tracks, eventsByTrack, frame, width, height, showDetections, detections])

  const highlight = useMemo(() => {
    if (selected === null) return null
    return tracks.find((t) => t.trackId === selected) ?? null
  }, [selected, tracks])

  if (!enabled) return null

  if (isLoading) {
    return (
      <div className="flex h-48 items-center justify-center rounded-xl border border-surface-800 bg-surface-950">
        <span className="text-sm text-surface-500">Loading tracks…</span>
      </div>
    )
  }

  if (isError) {
    return (
      <div className="rounded-xl border border-surface-800 bg-surface-950 p-5 text-sm text-red-400">
        Failed to load track data.
      </div>
    )
  }

  if (!tracks.length) {
    return (
      <div className="flex h-40 items-center justify-center rounded-xl border border-surface-800 bg-surface-950">
        <p className="text-sm text-surface-500">Run processing to generate tracks.</p>
      </div>
    )
  }

  const anyAtFrame = tracks.some((t) => t.points.some((p) => p.frameId === frame))

  return (
    <div className="rounded-xl border border-surface-800 bg-surface-950">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-surface-800 px-4 py-3">
        <div>
          <h2 className="font-medium text-surface-200">Track visualization</h2>
          <p className="text-xs text-surface-500">
            {tracks.length} track{tracks.length === 1 ? '' : 's'}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <label className="flex cursor-pointer items-center gap-1.5 text-xs text-surface-400">
            <input
              type="checkbox"
              checked={showDetections}
              onChange={(e) => setShowDetections(e.target.checked)}
              className="h-3.5 w-3.5 accent-orchard-500"
            />
            Detections
          </label>
          <label className="text-xs text-surface-400" htmlFor="track-frame">
            Frame
          </label>
          <input
            id="track-frame"
            type="range"
            min={0}
            max={maxFrame}
            value={frame}
            onChange={(e) => setFrame(Number(e.target.value))}
            className="h-2 w-40 cursor-pointer accent-orchard-500"
          />
          <span className="w-14 text-right text-xs tabular-nums text-surface-400">{frame}</span>
        </div>
      </div>

      <div className="p-4">
        <canvas
          ref={canvasRef}
          width={width}
          height={height}
          className="aspect-video w-full rounded-lg"
          style={{ width: '100%', height: 'auto' }}
        />
        {!anyAtFrame && (
          <p className="mt-2 text-center text-xs text-surface-600">
            No tracked fruit at this frame — scrub to a frame with detections.
          </p>
        )}
      </div>

      <div className="border-t border-surface-800">
        <h3 className="px-4 pt-3 text-xs font-medium tracking-wide text-surface-500 uppercase">
          Tracks
        </h3>
        <ul className="max-h-72 overflow-y-auto p-2">
          {tracks.map((track) => (
            <TrackRow
              key={track.id}
              track={track}
              highlighted={highlight?.id === track.id}
              onSelect={() => setSelected(selected === track.trackId ? null : track.trackId)}
              recovered={Boolean(
                (eventsByTrack.get(track.trackId) ?? []).some((event) => event.accepted),
              )}
              lost={!isTrackActive(track, maxFrame)}
            />
          ))}
        </ul>
      </div>
    </div>
  )
}

interface TrackRowProps {
  track: PersistedTrack
  highlighted: boolean
  recovered: boolean
  lost: boolean
  onSelect: () => void
}

function isTrackActive(track: PersistedTrack, maxFrame: number): boolean {
  const last = track.points[track.points.length - 1]?.frameId ?? 0
  return last >= Math.max(0, maxFrame - 1)
}

function TrackRow({ track, highlighted, recovered, lost, onSelect }: TrackRowProps) {
  const first = track.points[0]?.frameId ?? 0
  const last = track.points[track.points.length - 1]?.frameId ?? 0
  return (
    <li>
      <button
        type="button"
        onClick={onSelect}
        className={`flex w-full items-center justify-between gap-2 rounded-lg px-3 py-2 text-left transition-colors ${
          highlighted ? 'bg-surface-800' : 'hover:bg-surface-900'
        }`}
      >
        <span className="flex min-w-0 items-center gap-2">
          <span
            className="h-2.5 w-2.5 flex-shrink-0 rounded-full"
            style={{ backgroundColor: colorFor(track.trackId) }}
          />
          <span className="font-mono text-sm text-surface-200">#{track.trackId}</span>
          <span className="flex-shrink-0">
            {recovered ? (
              <span className="rounded-full bg-orchard-600/20 px-2 py-0.5 text-[10px] font-medium text-orchard-300">
                recovered
              </span>
            ) : lost ? (
              <span className="rounded-full bg-amber-500/15 px-2 py-0.5 text-[10px] font-medium text-amber-300">
                lost
              </span>
            ) : (
              <span className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-[10px] font-medium text-emerald-300">
                active
              </span>
            )}
          </span>
        </span>
        <span className="flex-shrink-0 text-xs text-surface-500">
          {first}–{last} · {track.points.length} obs · {averageConfidence(track).toFixed(2)}
        </span>
      </button>
    </li>
  )
}

function averageConfidence(track: PersistedTrack): number {
  if (!track.points.length) return 0
  return track.points.reduce((sum, p) => sum + p.confidence, 0) / track.points.length
}
