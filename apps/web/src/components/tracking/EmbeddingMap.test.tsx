import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { IdentityProjectionResponse } from '@orchardvision/types'
import { EmbeddingMap } from './EmbeddingMap'

const mocks = vi.hoisted(() => ({
  useIdentityProjection: vi.fn(),
}))

vi.mock('../../hooks/useVideos', () => ({
  useIdentityProjection: (videoId: string, enabled: boolean) =>
    mocks.useIdentityProjection(videoId, enabled),
}))

function renderMap(enabled = true) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <EmbeddingMap videoId="vid-1" enabled={enabled} />
    </QueryClientProvider>,
  )
}

const projection: IdentityProjectionResponse = {
  method: 'pca',
  total: 2,
  points: [
    { x: -0.4, y: 0.2, identityId: 0, quality: 0.9, observationCount: 12, isConfident: true },
    { x: 0.5, y: -0.3, identityId: 1, quality: 0.6, observationCount: 5, isConfident: false },
  ],
}

describe('EmbeddingMap', () => {
  it('renders a scatter plot with identity points', () => {
    mocks.useIdentityProjection.mockReturnValue({
      data: projection,
      isLoading: false,
      isError: false,
    })
    renderMap()
    const plot = screen.getByRole('img', { name: /embedding projection scatter/i })
    expect(plot).toBeInTheDocument()
    expect(screen.getByText(/PCA projection/)).toBeInTheDocument()
    expect(screen.getByTestId('embedding-point-0')).toBeInTheDocument()
    expect(screen.getByTestId('embedding-point-1')).toBeInTheDocument()
  })

  it('shows a loading placeholder while fetching', () => {
    mocks.useIdentityProjection.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    })
    renderMap()
    expect(screen.getByText(/Projecting embeddings/)).toBeInTheDocument()
  })

  it('shows an empty state when there are no identities', () => {
    mocks.useIdentityProjection.mockReturnValue({
      data: { method: 'pca', total: 0, points: [] },
      isLoading: false,
      isError: false,
    })
    renderMap()
    expect(screen.getByText(/Run processing to project identity embeddings/)).toBeInTheDocument()
  })

  it('renders nothing when disabled', () => {
    renderMap(false)
    expect(screen.queryByText(/embedding/i)).not.toBeInTheDocument()
  })
})
