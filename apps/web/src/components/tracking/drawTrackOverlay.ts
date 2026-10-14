import type {
  PersistedDetection,
  PersistedReidEvent,
  PersistedTrack,
  PersistedTrackPoint,
} from '@orchardvision/types'

export const TRACK_PALETTE = [
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

export function trackColor(trackId: number): string {
  return TRACK_PALETTE[trackId % TRACK_PALETTE.length]
}

const REFERENCE_DIAGONAL = Math.hypot(960, 540)

export function overlayScale(width: number, height: number): number {
  return Math.max(0.5, Math.hypot(width, height) / REFERENCE_DIAGONAL)
}

function centerOf(bbox: [number, number, number, number]): [number, number] {
  const [x, y, w, h] = bbox
  return [x + w / 2, y + h / 2]
}

function drawMarker(
  ctx: CanvasRenderingContext2D,
  bbox: [number, number, number, number],
  color: string,
  glyph: string,
  scale: number,
) {
  const [cx, cy] = centerOf(bbox)
  ctx.save()
  ctx.font = `${Math.round(14 * scale)}px ui-sans-serif, system-ui`
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.fillStyle = color
  ctx.globalAlpha = 1
  ctx.strokeStyle = 'rgba(15, 23, 42, 0.9)'
  ctx.lineWidth = 3 * scale
  ctx.strokeText(glyph, cx, cy - 16 * scale)
  ctx.fillText(glyph, cx, cy - 16 * scale)
  ctx.restore()
}

function drawOcclusionBand(
  ctx: CanvasRenderingContext2D,
  bbox: [number, number, number, number],
  scale: number,
) {
  const [x, y, w, h] = bbox
  ctx.save()
  ctx.globalAlpha = 0.16
  ctx.fillStyle = '#f59e0b'
  ctx.fillRect(x, y, w, h)
  ctx.restore()
  ctx.save()
  ctx.setLineDash([4 * scale, 4 * scale])
  ctx.strokeStyle = 'rgba(251, 191, 36, 0.55)'
  ctx.lineWidth = 1 * scale
  ctx.strokeRect(x - 3 * scale, y - 3 * scale, w + 6 * scale, h + 6 * scale)
  ctx.restore()
}

export interface TrackOverlayState {
  tracks: PersistedTrack[]
  eventsByTrack: Map<number, PersistedReidEvent[]>
  frame: number
  width: number
  height: number
  showDetections: boolean
  detections: PersistedDetection[]
  background?: string | null
  /** Decoded video frame drawn behind the overlay; replaces the background fill. */
  frameImage?: CanvasImageSource | null
}

function pointAt(
  track: PersistedTrack,
  targetFrame: number,
  edge: 'before' | 'after',
): PersistedTrackPoint | null {
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

export function drawTrackOverlay(ctx: CanvasRenderingContext2D, state: TrackOverlayState) {
  const {
    tracks,
    eventsByTrack,
    frame,
    width,
    height,
    showDetections,
    detections,
    background = 'rgba(15, 23, 42, 0.25)',
    frameImage = null,
  } = state

  const scale = overlayScale(width, height)

  ctx.clearRect(0, 0, width, height)
  if (frameImage) {
    ctx.drawImage(frameImage, 0, 0, width, height)
  }
  if (background && !frameImage) {
    ctx.fillStyle = background
    ctx.fillRect(0, 0, width, height)
  }

  for (const track of tracks) {
    const id = track.identityId ?? track.trackId
    const color = trackColor(id)
    const visible = track.points.filter((p) => p.frameId <= frame)

    if (visible.length >= 2) {
      ctx.beginPath()
      ctx.moveTo(centerOf(visible[0].bbox)[0], centerOf(visible[0].bbox)[1])
      for (const p of visible.slice(1)) {
        ctx.lineTo(centerOf(p.bbox)[0], centerOf(p.bbox)[1])
      }
      ctx.strokeStyle = color
      ctx.globalAlpha = 0.6
      ctx.lineWidth = 1.5 * scale
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
      ctx.lineWidth = 2 * scale
      ctx.stroke()
      ctx.fillStyle = color
      ctx.globalAlpha = 0.28
      ctx.fillRect(x, y, w, h)
      ctx.globalAlpha = 1
      ctx.font = `${Math.round(12 * scale)}px ui-sans-serif, system-ui`
      ctx.fillText(`#${id}`, x, Math.max(y - 4 * scale, 12 * scale))
    }

    const trackEvents = eventsByTrack.get(track.trackId) ?? []
    for (const event of trackEvents) {
      if (event.accepted && frame >= event.lostFrameId) {
        const lostPoint = pointAt(track, event.lostFrameId, 'before')
        const reappearPoint = pointAt(track, event.reappearanceFrameId, 'after')
        if (lostPoint) drawMarker(ctx, lostPoint.bbox, '#fb7185', '×', scale)
        if (reappearPoint) drawMarker(ctx, reappearPoint.bbox, '#34d399', '✓', scale)
        if (frame > event.lostFrameId && frame < event.reappearanceFrameId) {
          const gapPoint = pointAt(track, frame, 'before')
          if (gapPoint) drawOcclusionBand(ctx, gapPoint.bbox, scale)
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
      ctx.setLineDash([4 * scale, 4 * scale])
      ctx.lineWidth = 1.25 * scale
      ctx.stroke()
      ctx.setLineDash([])
      ctx.globalAlpha = 1
      ctx.font = `${Math.round(10 * scale)}px ui-sans-serif, system-ui`
      ctx.fillStyle = 'rgba(226, 232, 240, 0.9)'
      ctx.fillText(
        `d${det.confidence.toFixed(2)}${det.isOccluded ? '·occ' : ''}`,
        x,
        Math.max(y + h + 11 * scale, 12 * scale),
      )
      if (det.isOccluded) {
        ctx.beginPath()
        ctx.rect(x - 2 * scale, y - 2 * scale, w + 4 * scale, h + 4 * scale)
        ctx.strokeStyle = 'rgba(251, 191, 36, 0.85)'
        ctx.setLineDash([3 * scale, 3 * scale])
        ctx.lineWidth = 1.5 * scale
        ctx.stroke()
        ctx.setLineDash([])
      }
    }
  }
}
