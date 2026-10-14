import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, waitFor } from '@testing-library/react'
import { TrackVisualizer } from './TrackVisualizer'

const tracks = {
  tracks: [
    {
      id: 'tr1',
      videoId: 'v1',
      jobId: 'j1',
      trackId: 1,
      identityId: null,
      status: 'active',
      createdAt: null,
      points: [
        { frameId: 0, bbox: [10, 10, 20, 20], confidence: 0.9, isOccluded: false },
        { frameId: 1, bbox: [12, 12, 20, 20], confidence: 0.8, isOccluded: false },
      ],
    },
  ],
}

vi.mock('../../hooks/useVideos', () => ({
  useTracks: () => ({ data: tracks, isLoading: false, isError: false }),
  useReidEvents: () => ({ data: { events: [] } }),
  useFrameDetections: () => ({ data: { detections: [] } }),
}))

vi.mock('../../api/videos', () => ({
  videoFrameUrl: (id: string, frameId: number) => `/api/videos/${id}/frames/${frameId}`,
}))

describe('TrackVisualizer', () => {
  let drawImage: ReturnType<typeof vi.fn>
  let fillRect: ReturnType<typeof vi.fn>

  beforeEach(() => {
    drawImage = vi.fn()
    fillRect = vi.fn()
    vi.stubGlobal(
      'Image',
      class {
        onload: (() => void) | null = null
        complete = false
        naturalWidth = 320
        naturalHeight = 180
        src: string
        constructor(src: string) {
          this.src = src
          queueMicrotask(() => {
            this.complete = true
            this.onload?.()
          })
        }
      },
    )
    HTMLCanvasElement.prototype.getContext = vi.fn(() => ({
      drawImage,
      fillRect,
      clearRect: vi.fn(),
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
    })) as unknown as HTMLCanvasElement['getContext']
  })

  it('paints the video frame behind the track overlay', async () => {
    render(<TrackVisualizer videoId="v1" width={320} height={180} frameCount={2} enabled />)
    await waitFor(() => expect(drawImage).toHaveBeenCalled())
    expect(drawImage.mock.calls[0][0]).toMatchObject({ src: '/api/videos/v1/frames/0' })
    expect(drawImage.mock.calls[0].slice(1)).toEqual([0, 0, 320, 180])
  })
})
