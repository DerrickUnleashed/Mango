import { useEffect, useMemo, useRef, useState } from 'react'
import type { PersistedReidEvent } from '@orchardvision/types'
import { useFrameDetections, useReidEvents, useTracks } from '../../hooks/useVideos'
import { drawTrackOverlay } from './drawTrackOverlay'

interface VideoTrackingOverlayProps {
  videoId: string
  videoRef: React.RefObject<HTMLVideoElement | null>
  width: number
  height: number
  frameCount: number
  fps: number
  enabled: boolean
}

export function VideoTrackingOverlay({
  videoId,
  videoRef,
  width,
  height,
  frameCount,
  fps,
  enabled,
}: VideoTrackingOverlayProps) {
  const { data } = useTracks(videoId, enabled)
  const { data: reidData } = useReidEvents(videoId, enabled)
  const tracks = useMemo(() => data?.tracks ?? [], [data])
  const eventsByTrack = useMemo(() => {
    const map = new Map<number, PersistedReidEvent[]>()
    for (const event of reidData?.events ?? []) {
      const list = map.get(event.trackId) ?? []
      list.push(event)
      map.set(event.trackId, list)
    }
    return map
  }, [reidData])

  const [frame, setFrame] = useState(0)
  const [showDetections, setShowDetections] = useState(true)
  const { data: detectionsData } = useFrameDetections(videoId, frame, enabled && showDetections)
  const detections = useMemo(() => detectionsData?.detections ?? [], [detectionsData])
  const canvasRef = useRef<HTMLCanvasElement | null>(null)

  useEffect(() => {
    const video = videoRef.current
    if (!video || !enabled) return
    const sync = () => {
      const raw = Math.round(video.currentTime * fps)
      setFrame(Math.max(0, Math.min(Math.round(frameCount - 1), raw)))
    }
    sync()
    video.addEventListener('timeupdate', sync)
    video.addEventListener('seeked', sync)
    return () => {
      video.removeEventListener('timeupdate', sync)
      video.removeEventListener('seeked', sync)
    }
  }, [videoRef, enabled, fps, frameCount])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    if (!tracks.length && !detections.length) {
      ctx.clearRect(0, 0, width, height)
      return
    }

    drawTrackOverlay(ctx, {
      tracks,
      eventsByTrack,
      frame,
      width,
      height,
      showDetections,
      detections,
      background: null,
    })
  }, [tracks, eventsByTrack, frame, width, height, showDetections, detections])

  return (
    <>
      <canvas
        ref={canvasRef}
        width={width}
        height={height}
        className="pointer-events-none absolute inset-0 h-full w-full"
        aria-hidden="true"
      />
      {tracks.length > 0 && (
        <label className="absolute right-2 bottom-2 z-10 flex cursor-pointer items-center gap-1.5 rounded-md bg-black/60 px-2 py-1 text-xs font-medium text-white">
          <input
            type="checkbox"
            checked={showDetections}
            onChange={(e) => setShowDetections(e.target.checked)}
            className="h-3.5 w-3.5 accent-orchard-500"
          />
          Detections
        </label>
      )}
    </>
  )
}
