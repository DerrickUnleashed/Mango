import { describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { Experiment } from '@orchardvision/types'
import { ExperimentsPage } from './ExperimentsPage'

const mocks = vi.hoisted(() => {
  const completed: Experiment = {
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
  return {
    getExperiments: vi.fn(),
    createExperiment: vi.fn(),
    deleteExperiment: vi.fn(),
    exportExperiment: vi.fn(),
    completed,
    withRuns: true,
  }
})

vi.mock('../api/experiments', () => ({
  getExperiments: mocks.getExperiments,
  createExperiment: mocks.createExperiment,
  deleteExperiment: mocks.deleteExperiment,
  exportExperiment: mocks.exportExperiment,
}))

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={client}>
      <ExperimentsPage />
    </QueryClientProvider>,
  )
}

describe('ExperimentsPage', () => {
  it('renders an empty state without runs', async () => {
    mocks.withRuns = false
    mocks.getExperiments.mockResolvedValue({ experiments: [], total: 0 })
    renderPage()
    expect(
      await screen.findByText('No experiments yet — pick a tracker above and run one.'),
    ).toBeInTheDocument()
  })

  it('renders experiment results with metrics', async () => {
    mocks.withRuns = true
    mocks.getExperiments.mockResolvedValue({ experiments: [mocks.completed], total: 1 })
    renderPage()
    expect(await screen.findByText('mock run')).toBeInTheDocument()
    expect(screen.getByText('0.823')).toBeInTheDocument()
    expect(screen.getByText('12.3')).toBeInTheDocument()
  })

  it('starts a run with the selected tracker', async () => {
    mocks.withRuns = false
    mocks.getExperiments.mockResolvedValue({ experiments: [], total: 0 })
    mocks.createExperiment.mockResolvedValue({
      ...mocks.completed,
      id: 'exp-2',
      status: 'running',
      metrics: null,
    })
    renderPage()
    await screen.findByText('No experiments yet — pick a tracker above and run one.')
    fireEvent.click(screen.getByRole('button', { name: 'Run experiment' }))
    await waitFor(() =>
      expect(mocks.createExperiment).toHaveBeenCalledWith(
        { tracker: 'mock', num_frames: 310 },
        expect.anything(),
      ),
    )
  })
})
