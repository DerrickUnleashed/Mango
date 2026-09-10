import { describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent } from '@testing-library/react'
import { SettingsPage } from './SettingsPage'

const mocks = vi.hoisted(() => ({
  getSettings: vi.fn(),
  updateSettings: vi.fn(),
  push: vi.fn(),
}))

vi.mock('../components/ui/useToast', () => ({
  useToast: () => ({ push: mocks.push }),
}))

vi.mock('../api/settings', () => ({
  getSettings: mocks.getSettings,
  updateSettings: mocks.updateSettings,
}))

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={client}>
      <SettingsPage />
    </QueryClientProvider>,
  )
}

describe('SettingsPage', () => {
  it('loads and renders default pipeline values', async () => {
    mocks.getSettings.mockResolvedValue({
      values: {
        confidenceThreshold: 0.35,
        reidThreshold: 0.6,
        memoryUpdateRate: 0.2,
        occlusionTimeoutSec: 30,
        cameraMotionMode: 'static',
      },
      revision: 1,
      updatedAt: '2026-09-10T00:00:00Z',
    })
    mocks.updateSettings.mockResolvedValue({
      values: {},
      revision: 2,
      updatedAt: null,
    })
    renderPage()
    expect(screen.getByRole('heading', { name: 'Settings' })).toBeInTheDocument()
    expect(screen.getByLabelText('Re-ID threshold')).toBeInTheDocument()
  })

  it('submits the edited values to the API', async () => {
    renderPage()
    const reid = screen.getByLabelText('Re-ID threshold')
    fireEvent.change(reid, { target: { value: '0.5' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save settings' }))
    await waitFor(() =>
      expect(mocks.updateSettings).toHaveBeenCalledWith(
        {
          values: {
            confidenceThreshold: 0.35,
            reidThreshold: 0.5,
            memoryUpdateRate: 0.2,
            occlusionTimeoutSec: 30,
            cameraMotionMode: 'static',
          },
        },
        expect.anything(),
      ),
    )
    expect(await screen.findByText('Saved')).toBeInTheDocument()
  })
})
