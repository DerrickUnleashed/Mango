import { useEffect, useMemo, useRef, useState } from 'react'
import type { PersistedReidEvent, PersistedTrack } from '@orchardvision/types'
import { useFrameDetections, useReidEvents, useTracks } from '../../hooks/useVideos'
import { trackColor, drawTrackOverlay } from './drawTrackOverlay'

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

    drawTrackOverlay(ctx, {
      tracks,
      eventsByTrack,
      frame,
      width,
      height,
      showDetections,
      detections,
    })
  }, [tracks, eventsByTrack, frame, width, height, showDetections, detections])

  const highlight = useMemo(() => {
    if (selected === null) return null
    return tracks.find((t) => t.trackId === selected) ?? null
  }, [selected, tracks])

  if (!enabled) return null

  if (isLoading) {
    return (
      <div className="flex h-48 items-center justify-center glass card-glow rounded-2xl">
        <span className="text-sm text-surface-500">Loading tracks…</span>
      </div>
    )
  }

  if (isError) {
    return (
      <div className="glass card-glow rounded-2xl p-5 text-sm text-red-400">
        Failed to load track data.
      </div>
    )
  }

  if (!tracks.length) {
    return (
      <div className="flex h-40 items-center justify-center glass card-glow rounded-2xl">
        <p className="text-sm text-surface-500">Run processing to generate tracks.</p>
      </div>
    )
  }

  const anyAtFrame = tracks.some((t) => t.points.some((p) => p.frameId === frame))

  return (
    <div className="glass card-glow rounded-2xl">
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
            style={{ backgroundColor: trackColor(track.trackId) }}
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
