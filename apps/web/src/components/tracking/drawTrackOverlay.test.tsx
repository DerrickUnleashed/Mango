import { describe, expect, it, vi } from 'vitest'
import { drawTrackOverlay } from './drawTrackOverlay'
import type { PersistedTrack } from '@orchardvision/types'

const track: PersistedTrack = {
  id: 't1',
  videoId: 'v',
  jobId: 'j',
  trackId: 1,
  identityId: null,
  status: 'active',
  createdAt: null,
  points: [{ frameId: 0, bbox: [10, 10, 20, 20], confidence: 0.9, isOccluded: false }],
}

function makeCtx() {
  return {
    clearRect: vi.fn(),
    fillRect: vi.fn(),
    drawImage: vi.fn(),
    save: vi.fn(),
    restore: vi.fn(),
    beginPath: vi.fn(),
    closePath: vi.fn(),
    moveTo: vi.fn(),
    lineTo: vi.fn(),
    stroke: vi.fn(),
    fill: vi.fn(),
    rect: vi.fn(),
    fillText: vi.fn(),
    strokeText: vi.fn(),
    setLineDash: vi.fn(),
    fillStyle: '',
    strokeStyle: '',
    lineWidth: 1,
    font: '',
    textAlign: '',
    textBaseline: '',
    globalAlpha: 1,
  } as unknown as CanvasRenderingContext2D & { fillRect: ReturnType<typeof vi.fn> }
}

describe('drawTrackOverlay', () => {
  it('paints the frame image instead of the background fill when one is given', () => {
    const ctx = makeCtx()
    const frameImage = { src: 'frame' } as unknown as CanvasImageSource
    drawTrackOverlay(ctx, {
      tracks: [track],
      eventsByTrack: new Map(),
      frame: 0,
      width: 320,
      height: 180,
      showDetections: false,
      detections: [],
      frameImage,
    })
    expect(ctx.drawImage).toHaveBeenCalledWith(frameImage, 0, 0, 320, 180)
    const fullCanvasFills = ctx.fillRect.mock.calls.filter(
      ([x, y, w, h]) => x === 0 && y === 0 && w === 320 && h === 180,
    )
    expect(fullCanvasFills).toHaveLength(0)
  })

  it('keeps the background fill when no frame image is given', () => {
    const ctx = makeCtx()
    drawTrackOverlay(ctx, {
      tracks: [track],
      eventsByTrack: new Map(),
      frame: 0,
      width: 320,
      height: 180,
      showDetections: false,
      detections: [],
    })
    const fullCanvasFills = ctx.fillRect.mock.calls.filter(
      ([x, y, w, h]) => x === 0 && y === 0 && w === 320 && h === 180,
    )
    expect(fullCanvasFills).toHaveLength(1)
  })
})
