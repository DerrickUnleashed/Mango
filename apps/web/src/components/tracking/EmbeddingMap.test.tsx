import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ObservationProjectionResponse } from '@orchardvision/types'
import { EmbeddingMap } from './EmbeddingMap'

const mocks = vi.hoisted(() => ({
  useObservationProjection: vi.fn(),
}))

vi.mock('../../hooks/useVideos', () => ({
  useObservationProjection: (videoId: string, method: string, enabled: boolean) =>
    mocks.useObservationProjection(videoId, method, enabled),
}))

function renderMap(enabled = true) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <EmbeddingMap videoId="vid-1" enabled={enabled} />
    </QueryClientProvider>,
  )
}

const projection: ObservationProjectionResponse = {
  method: 'pca',
  total: 2,
  points: [
    { x: -0.4, y: 0.2, identityId: 0, frameId: 3, trackId: 7, confidence: 0.9, isOccluded: false },
    { x: 0.5, y: -0.3, identityId: 1, frameId: 9, trackId: 8, confidence: 0.6, isOccluded: true },
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
    renderMap(false)
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
})
