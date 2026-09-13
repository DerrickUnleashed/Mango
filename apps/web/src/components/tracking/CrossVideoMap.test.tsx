import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { CrossVideoProjectionResponse, Video } from '@orchardvision/types'
import { CrossVideoMap } from './CrossVideoMap'

const mocks = vi.hoisted(() => ({
  useCrossVideoProjection: vi.fn(),
}))

vi.mock('../../hooks/useVideos', () => ({
  useCrossVideoProjection: (method: string, enabled: boolean) =>
    mocks.useCrossVideoProjection(method, enabled),
}))

const videos: Video[] = [
  {
    id: 'vid-1',
    filename: 'a.mp4',
    originalName: 'Orchard A.mp4',
    mimeType: 'video/mp4',
    sizeBytes: 1234,
    width: 640,
    height: 360,
    frameCount: 30,
    fps: 30,
    durationSeconds: 1,
    codec: 'mp4v',
    status: 'processed',
    createdAt: '2026-09-10T00:00:00Z',
    processingJob: null,
  },
  {
    id: 'vid-2',
    filename: 'b.mp4',
    originalName: 'Orchard B.mp4',
    mimeType: 'video/mp4',
    sizeBytes: 1234,
    width: 1280,
    height: 720,
    frameCount: 30,
    fps: 30,
    durationSeconds: 1,
    codec: 'mp4v',
    status: 'processed',
    createdAt: '2026-09-10T00:00:01Z',
    processingJob: null,
  },
]

function renderMap(enabled = true) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <CrossVideoMap videos={videos} enabled={enabled} />
    </QueryClientProvider>,
  )
}

const projection: CrossVideoProjectionResponse = {
  method: 'umap',
  total: 2,
  videoCount: 2,
  points: [
    {
      x: -0.5,
      y: 0.3,
      videoId: 'vid-1',
      identityId: 0,
      frameId: 3,
      trackId: 7,
      bbox: [10, 20, 40, 40],
      confidence: 0.9,
      isOccluded: false,
      qualityScore: 0.971,
    },
    {
      x: 0.6,
      y: -0.2,
      videoId: 'vid-2',
      identityId: 1,
      frameId: 9,
      trackId: 8,
      bbox: null,
      confidence: 0.6,
      isOccluded: true,
      qualityScore: null,
    },
  ],
}

describe('CrossVideoMap', () => {
  it('renders a projection across videos with a legend', () => {
    mocks.useCrossVideoProjection.mockReturnValue({
      data: projection,
      isLoading: false,
      isError: false,
    })
    renderMap()
    expect(
      screen.getByRole('img', { name: /cross-video embedding projection/i }),
    ).toBeInTheDocument()
    expect(screen.getByText(/2 observations · 2 videos/)).toBeInTheDocument()
    expect(screen.getByText('Orchard A.mp4')).toBeInTheDocument()
    expect(screen.getByText('Orchard B.mp4')).toBeInTheDocument()
    expect(screen.getByTestId('cross-video-point-vid-1-0-3')).toBeInTheDocument()
    expect(screen.getByTestId('cross-video-point-vid-2-1-9')).toBeInTheDocument()
  })

  it('shows the loading placeholder while fetching', () => {
    mocks.useCrossVideoProjection.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    })
    renderMap()
    expect(screen.getByText(/Projecting cross-video embeddings/)).toBeInTheDocument()
  })

  it('shows an empty state when nothing has been processed', () => {
    mocks.useCrossVideoProjection.mockReturnValue({
      data: { method: 'pca', total: 0, videoCount: 0, points: [] },
      isLoading: false,
      isError: false,
    })
    renderMap()
    expect(screen.getByText(/Process at least one video/)).toBeInTheDocument()
  })

  it('renders nothing when disabled', () => {
    renderMap(false)
    expect(screen.queryByText(/embedding|observations/i)).not.toBeInTheDocument()
  })

  it('shows a bbox crop popup with video metadata on hover', () => {
    mocks.useCrossVideoProjection.mockReturnValue({
      data: projection,
      isLoading: false,
      isError: false,
    })
    renderMap()
    fireEvent.mouseEnter(screen.getByTestId('cross-video-point-vid-1-0-3'))
    expect(screen.getByRole('status')).toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'Crop of frame 3' })).toBeInTheDocument()
    expect(screen.getByText(/Orchard A.mp4 · id-0 · f3 · track 7/)).toBeInTheDocument()
    expect(screen.getByText(/proto sim 0.971/)).toBeInTheDocument()
  })

  it('switches projection method and refetches', () => {
    mocks.useCrossVideoProjection.mockReturnValue({
      data: projection,
      isLoading: false,
      isError: false,
    })
    renderMap()
    fireEvent.click(screen.getByRole('tab', { name: /PCA/i }))
    expect(mocks.useCrossVideoProjection).toHaveBeenLastCalledWith('pca', true)
  })
})
