import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import type { Video } from '@orchardvision/types'
import { VideoDetailPage } from './VideoDetailPage'

const mocks = vi.hoisted(() => {
  const makeVideo = (withJob: boolean): Video => ({
    id: 'vid-1',
    filename: 'orchard-a.mp4',
    originalName: 'Orchard A.mp4',
    mimeType: 'video/mp4',
    sizeBytes: 1234,
    width: 640,
    height: 360,
    frameCount: 30,
    fps: 30,
    durationSeconds: 1,
    codec: 'mp4v',
    status: 'uploaded',
    createdAt: '2026-09-10T00:00:00Z',
    processingJob: withJob
      ? {
          id: 'job-1',
          videoId: 'vid-1',
          status: 'running',
          stage: 'tracking',
          progress: 55,
          error: null,
          message: 'Tracking detections',
          inferenceMode: 'mock',
          startedAt: null,
          completedAt: null,
          createdAt: '2026-09-10T00:00:00Z',
          config: {
            inference_mode: 'mock',
            confidence_threshold: 0.35,
            tracker: 'mock',
            camera_motion: 'static',
            reid_threshold: 0.6,
            memory_update_rate: 0.2,
            tracker_match_threshold: 120,
            tracker_buffer_frames: 30,
            max_frames: null,
          },
        }
      : null,
  })
  return { mutate: vi.fn(), makeVideo, withJob: true }
})

vi.mock('react-router-dom', () => ({
  useParams: () => ({ videoId: 'vid-1' }),
}))

vi.mock('../components/ui/useToast', () => ({
  useToast: () => ({ push: vi.fn() }),
}))

vi.mock('../hooks/useVideos', () => ({
  useVideo: () => ({
    data: mocks.makeVideo(mocks.withJob),
    isLoading: false,
    isError: false,
  }),
  useProcessVideo: () => ({ mutate: mocks.mutate, isPending: false }),
}))

vi.mock('../hooks/useSettings', () => ({
  useSettings: () => ({ data: undefined, isLoading: false }),
}))

describe('VideoDetailPage', () => {
  it('shows job progress message while processing', () => {
    mocks.withJob = true
    render(<VideoDetailPage />)
    expect(screen.getByRole('heading', { name: 'Orchard A.mp4' })).toBeInTheDocument()
    expect(screen.getByText(/Status: running · Tracking detections/)).toBeInTheDocument()
  })

  it('renders a playable video preview of the uploaded source', () => {
    mocks.withJob = true
    render(<VideoDetailPage />)
    const player = screen.getByLabelText('Video preview for Orchard A.mp4') as HTMLVideoElement
    expect(player).toBeInTheDocument()
    expect(player.src).toContain('/api/videos/vid-1/file')
  })

  it('renders the persisted pipeline configuration for a job', () => {
    mocks.withJob = true
    render(<VideoDetailPage />)
    expect(screen.getAllByText('mock')).toHaveLength(2)
    expect(screen.getByText('0.35')).toBeInTheDocument()
    expect(screen.getByText('static')).toBeInTheDocument()
    expect(screen.getByText('0.60')).toBeInTheDocument()
    expect(screen.getByText('0.20')).toBeInTheDocument()
  })

  it('hides pipeline configuration when there is no job', () => {
    mocks.withJob = false
    render(<VideoDetailPage />)
    expect(screen.queryByText('0.60')).not.toBeInTheDocument()
    expect(
      screen.getByText('Run the analysis pipeline to detect, track, and re-identify fruits.'),
    ).toBeInTheDocument()
  })

  it('offers the TAPNext++ tracker alongside box trackers', () => {
    mocks.withJob = false
    render(<VideoDetailPage />)
    const tracker = screen.getByLabelText('Tracker') as HTMLSelectElement
    expect(tracker.value).toBe('bytetrack')
    expect(Array.from(tracker.options).map((option) => option.value)).toEqual([
      'bytetrack',
      'tapnext',
      'mock',
    ])
  })
})
