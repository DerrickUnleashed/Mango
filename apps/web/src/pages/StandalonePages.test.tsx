import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { Video } from '@orchardvision/types'
import { ToastProvider } from '../components/ui/Toast'
import { AnalyticsPage } from './AnalyticsPage'
import { EvaluationPage } from './EvaluationPage'
import { IdentitiesPage } from './IdentitiesPage'
import { ReidentificationPage } from './ReidentificationPage'

const mocks = vi.hoisted(() => {
  const makeVideo = (id: string, originalName: string, status: Video['status']): Video => ({
    id,
    filename: `${id}.mp4`,
    originalName,
    mimeType: 'video/mp4',
    sizeBytes: 1234,
    width: 640,
    height: 360,
    frameCount: 30,
    fps: 30,
    durationSeconds: 1,
    codec: 'mp4v',
    status,
    createdAt: '2026-09-10T00:00:00Z',
    processingJob: null,
  })
  return {
    makeVideo,
    getExperiments: vi.fn(),
    processed: [makeVideo('vid-1', 'Orchard A.mp4', 'processed')],
  }
})

vi.mock('../hooks/useVideos', () => ({
  useVideos: () => ({
    data: { videos: mocks.processed, total: mocks.processed.length },
    isLoading: false,
  }),
}))

vi.mock('../components/tracking/AnalyticsPanel', () => ({
  AnalyticsPanel: ({ videoId }: { videoId: string }) => (
    <div role="region" aria-label="analytics panel">
      Analytics panel for {videoId}
    </div>
  ),
}))

vi.mock('../components/tracking/IdentitiesPanel', () => ({
  IdentitiesPanel: ({ videoId }: { videoId: string }) => (
    <div role="region" aria-label="identities panel">
      Identities panel for {videoId}
    </div>
  ),
}))

vi.mock('../components/tracking/ReIdPanel', () => ({
  ReIdPanel: ({ videoId }: { videoId: string }) => (
    <div role="region" aria-label="reid panel">
      Re-id panel for {videoId}
    </div>
  ),
}))

vi.mock('../api/experiments', () => ({
  getExperiments: mocks.getExperiments,
  createExperiment: vi.fn(),
  deleteExperiment: vi.fn(),
  exportExperiment: vi.fn(),
}))

describe('standalone pages', () => {
  describe('AnalyticsPage', () => {
    it('shows the empty state when no processed videos exist', () => {
      mocks.processed.length = 0
      render(<AnalyticsPage />)
      expect(screen.getByText('Analytics will appear here')).toBeInTheDocument()
    })

    it('renders the analytics panel for the selected processed video', () => {
      mocks.processed = [mocks.makeVideo('vid-1', 'Orchard A.mp4', 'processed')]
      render(<AnalyticsPage />)
      expect(screen.getByLabelText('Select processed video')).toBeInTheDocument()
      expect(screen.getByRole('region', { name: 'analytics panel' })).toHaveTextContent(
        'Analytics panel for vid-1',
      )
    })

    it('switches the analytics panel to a newly selected video', () => {
      mocks.processed = [
        mocks.makeVideo('vid-1', 'Orchard A.mp4', 'processed'),
        mocks.makeVideo('vid-2', 'Orchard B.mp4', 'processed'),
      ]
      render(<AnalyticsPage />)
      fireEvent.change(screen.getByLabelText('Select processed video'), {
        target: { value: 'vid-2' },
      })
      expect(screen.getByRole('region', { name: 'analytics panel' })).toHaveTextContent(
        'Analytics panel for vid-2',
      )
    })
  })

  describe('IdentitiesPage', () => {
    it('shows the empty state when no processed videos exist', () => {
      mocks.processed.length = 0
      render(<IdentitiesPage />)
      expect(screen.getByText('No identities tracked yet')).toBeInTheDocument()
    })

    it('renders the identities panel for a processed video', () => {
      mocks.processed = [mocks.makeVideo('vid-1', 'Orchard A.mp4', 'processed')]
      render(<IdentitiesPage />)
      expect(screen.getByRole('region', { name: 'identities panel' })).toHaveTextContent(
        'Identities panel for vid-1',
      )
    })
  })

  describe('ReidentificationPage', () => {
    it('shows the empty state when no processed videos exist', () => {
      mocks.processed.length = 0
      render(<ReidentificationPage />)
      expect(screen.getByText('No re-identification events')).toBeInTheDocument()
    })

    it('renders the re-id panel for a processed video', () => {
      mocks.processed = [mocks.makeVideo('vid-1', 'Orchard A.mp4', 'processed')]
      render(<ReidentificationPage />)
      expect(screen.getByRole('region', { name: 'reid panel' })).toHaveTextContent(
        'Re-id panel for vid-1',
      )
    })
  })

  describe('EvaluationPage', () => {
    it('surfaces completed experiment results', async () => {
      const completed: import('@orchardvision/types').Experiment = {
        id: 'exp-1',
        name: 'mock run',
        status: 'completed',
        tracker: 'mock',
        scenario: 'orchard',
        numFrames: 310,
        config: null,
        metrics: {
          idf1: 0.823,
          hota: 0.712,
          idSwitches: 3,
          trackFragmentation: 0.05,
          countMae: 1.4,
          countMape: 12.3,
          identityRecoveryRate: 0.9,
        },
        error: null,
        createdAt: '2026-09-10T00:00:00Z',
        completedAt: '2026-09-10T00:01:00Z',
      }
      mocks.getExperiments.mockResolvedValue({ experiments: [completed], total: 1 })

      const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
      render(
        <ToastProvider>
          <QueryClientProvider client={client}>
            <EvaluationPage />
          </QueryClientProvider>
        </ToastProvider>,
      )

      expect(screen.getByRole('heading', { name: 'Evaluation' })).toBeInTheDocument()
      expect(await screen.findByText('mock run')).toBeInTheDocument()
      expect(screen.getByText('0.823')).toBeInTheDocument()
    })
  })
})
