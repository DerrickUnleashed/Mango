import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ObservationProjectionResponse } from '@orchardvision/types'
import { EmbeddingMap } from './EmbeddingMap'

const mocks = vi.hoisted(() => ({
  useObservationProjection: vi.fn(),
  useVideo: vi.fn(),
  useIdentityProjection: vi.fn(),
}))

vi.mock('../../hooks/useVideos', () => ({
  useObservationProjection: (videoId: string, method: string, enabled: boolean) =>
    mocks.useObservationProjection(videoId, method, enabled),
  useVideo: (videoId: string) => mocks.useVideo(videoId),
  useIdentityProjection: (videoId: string, method: string, enabled: boolean) =>
    mocks.useIdentityProjection(videoId, method, enabled),
}))

function renderMap(
  props: {
    enabled?: boolean
    onSeekFrame?: (frameId: number) => void
    onOpenIdentity?: (identityId: number) => void
  } = {},
) {
  mocks.useVideo.mockReturnValue({
    data: { id: 'vid-1', width: 640, height: 360, fps: 30 },
    isLoading: false,
    isError: false,
  })
  mocks.useIdentityProjection.mockReturnValue({
    data: { method: 'pca', total: 0, points: [] },
    isLoading: false,
    isError: false,
  })
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <EmbeddingMap videoId="vid-1" enabled={props.enabled ?? true} {...props} />
    </QueryClientProvider>,
  )
}

const projection: ObservationProjectionResponse = {
  method: 'pca',
  total: 2,
  points: [
    {
      x: -0.4,
      y: 0.2,
      identityId: 0,
      frameId: 3,
      trackId: 7,
      bbox: [10, 20, 40, 40],
      confidence: 0.9,
      isOccluded: false,
      qualityScore: 0.987,
    },
    {
      x: 0.5,
      y: -0.3,
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

const prototypes = {
  method: 'pca',
  total: 1,
  points: [
    {
      x: 0.1,
      y: 0.1,
      identityId: 0,
      quality: 0.92,
      observationCount: 12,
      isConfident: true,
    },
  ],
}

describe('EmbeddingMap', () => {
  it('renders a scatter plot with observation points', () => {
    mocks.useObservationProjection.mockReturnValue({
      data: projection,
      isLoading: false,
      isError: false,
    })
    renderMap()
    expect(screen.getByRole('img', { name: /embedding projection scatter/i })).toBeInTheDocument()
    expect(screen.getByText(/PCA projection/)).toBeInTheDocument()
    expect(screen.getByTestId('embedding-point-0-3')).toBeInTheDocument()
    expect(screen.getByTestId('embedding-point-1-9')).toBeInTheDocument()
  })

  it('shows a loading placeholder while fetching', () => {
    mocks.useObservationProjection.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    })
    renderMap()
    expect(screen.getByText(/Projecting embeddings/)).toBeInTheDocument()
  })

  it('shows an empty state when there are no observations', () => {
    mocks.useObservationProjection.mockReturnValue({
      data: { method: 'pca', total: 0, points: [] },
      isLoading: false,
      isError: false,
    })
    renderMap()
    expect(screen.getByText(/Run processing to project observation embeddings/)).toBeInTheDocument()
  })

  it('renders nothing when disabled', () => {
    renderMap({ enabled: false })
    expect(screen.queryByText(/embedding/i)).not.toBeInTheDocument()
  })

  it('switches projection method and refetches', () => {
    mocks.useObservationProjection.mockReturnValue({
      data: { ...projection, method: 'umap', points: projection.points.slice(0, 1) },
      isLoading: false,
      isError: false,
    })
    renderMap()
    fireEvent.click(screen.getByRole('tab', { name: /UMAP/i }))
    expect(mocks.useObservationProjection).toHaveBeenLastCalledWith('vid-1', 'umap', true)
    expect(screen.getByText(/UMAP projection/)).toBeInTheDocument()
  })

  it('shows a bbox crop popup when hovering a point with a bbox', () => {
    mocks.useObservationProjection.mockReturnValue({
      data: projection,
      isLoading: false,
      isError: false,
    })
    renderMap()
    fireEvent.mouseEnter(screen.getByTestId('embedding-point-0-3'))
    expect(screen.getByRole('status')).toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'Crop of frame 3' })).toBeInTheDocument()
    expect(screen.getByText(/id-0 · f3 · track 7/)).toBeInTheDocument()
  })

  it('shows a placeholder crop when hovering a point without a bbox', () => {
    mocks.useObservationProjection.mockReturnValue({
      data: projection,
      isLoading: false,
      isError: false,
    })
    renderMap()
    fireEvent.mouseEnter(screen.getByTestId('embedding-point-1-9'))
    expect(screen.getByRole('status')).toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'Crop of frame 9' })).toHaveTextContent('no bbox')
  })

  it('seeks the video and opens the identity when a point is clicked', () => {
    const onSeekFrame = vi.fn()
    const onOpenIdentity = vi.fn()
    mocks.useObservationProjection.mockReturnValue({
      data: projection,
      isLoading: false,
      isError: false,
    })
    renderMap({ onSeekFrame, onOpenIdentity })
    fireEvent.click(screen.getByTestId('embedding-point-0-3'))
    expect(onSeekFrame).toHaveBeenCalledWith(3)
    expect(onOpenIdentity).toHaveBeenCalledWith(0)
  })

  it('exposes seek and identity actions from the popup', () => {
    const onSeekFrame = vi.fn()
    const onOpenIdentity = vi.fn()
    mocks.useObservationProjection.mockReturnValue({
      data: projection,
      isLoading: false,
      isError: false,
    })
    renderMap({ onSeekFrame, onOpenIdentity })
    fireEvent.mouseEnter(screen.getByTestId('embedding-point-0-3'))
    fireEvent.click(screen.getByRole('button', { name: /seek frame/i }))
    expect(onSeekFrame).toHaveBeenCalledWith(3)
    fireEvent.click(screen.getByRole('button', { name: /view identity/i }))
    expect(onOpenIdentity).toHaveBeenCalledWith(0)
  })

  it('shows the prototype simulation score in the observation popup', () => {
    mocks.useObservationProjection.mockReturnValue({
      data: projection,
      isLoading: false,
      isError: false,
    })
    renderMap()
    fireEvent.mouseEnter(screen.getByTestId('embedding-point-0-3'))
    expect(screen.getByText(/proto sim 0.987/)).toBeInTheDocument()
  })

  it('shows identity centroids when the toggle is enabled', () => {
    mocks.useObservationProjection.mockReturnValue({
      data: projection,
      isLoading: false,
      isError: false,
    })
    renderMap()
    mocks.useIdentityProjection.mockReturnValue({
      data: prototypes,
      isLoading: false,
      isError: false,
    })
    expect(screen.queryByTestId('embedding-prototype-0')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('checkbox', { name: /identity centroids/i }))
    expect(mocks.useIdentityProjection).toHaveBeenLastCalledWith('vid-1', 'tsne', true)
    expect(screen.getByTestId('embedding-prototype-0')).toBeInTheDocument()
    fireEvent.mouseEnter(screen.getByTestId('embedding-prototype-0'))
    expect(screen.getByText(/prototype centroid/)).toBeInTheDocument()
    expect(screen.getByText(/q 0.92 · 12 obs · confident/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('checkbox', { name: /identity centroids/i }))
    expect(screen.queryByTestId('embedding-prototype-0')).not.toBeInTheDocument()
  })

  it('hides centroids even when the projection query still holds cached data', () => {
    mocks.useObservationProjection.mockReturnValue({
      data: projection,
      isLoading: false,
      isError: false,
    })
    renderMap()
    mocks.useIdentityProjection.mockReturnValue({
      data: prototypes,
      isLoading: false,
      isError: false,
    })
    fireEvent.click(screen.getByRole('checkbox', { name: /identity centroids/i }))
    expect(screen.getByTestId('embedding-prototype-0')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('checkbox', { name: /identity centroids/i }))
    expect(screen.queryByTestId('embedding-prototype-0')).not.toBeInTheDocument()
    expect(screen.queryByText(/prototype centroid/)).not.toBeInTheDocument()
  })
})
