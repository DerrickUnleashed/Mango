import { describe, expect, it, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import type { PersistedReidEvent } from '@orchardvision/types'
import { ReIdPanel } from './ReIdPanel'

const mocks = vi.hoisted(() => ({
  useReidEvents: vi.fn(),
}))

vi.mock('../../hooks/useVideos', () => ({
  useReidEvents: (videoId: string, enabled: boolean) => mocks.useReidEvents(videoId, enabled),
}))

const baseEvent: PersistedReidEvent = {
  id: 'e1',
  videoId: 'vid-1',
  trackId: 2,
  victimTrackId: 1,
  identityId: 7,
  lostFrameId: 4,
  reappearanceFrameId: 12,
  similarity: 0.93,
  confidence: 0.95,
  accepted: true,
  createdAt: null,
}

function renderPanel(events: PersistedReidEvent[], enabled = true) {
  mocks.useReidEvents.mockReturnValue({ data: { events }, isLoading: false, isError: false })
  return render(<ReIdPanel videoId="vid-1" enabled={enabled} />)
}

describe('ReIdPanel', () => {
  it('renders an empty event list', () => {
    renderPanel([])
    expect(screen.getByText(/No re-identifications in this run/)).toBeInTheDocument()
  })

  it('renders events with recovered badges', () => {
    renderPanel([baseEvent])
    expect(screen.getByText(/track #2 → id-7/)).toBeInTheDocument()
    expect(screen.getByText(/recovered/)).toBeInTheDocument()
    expect(screen.getByText(/1 event · 1 accepted/)).toBeInTheDocument()
  })

  it('shows competing candidates after expanding a row', () => {
    const event: PersistedReidEvent = {
      ...baseEvent,
      candidateIdentityIds: [3, 7, 9],
      candidateScores: { '3': 0.71, '7': 0.93, '9': 0.66 },
    }
    renderPanel([event])
    expect(screen.queryByText(/Candidate comparison/)).not.toBeInTheDocument()
    fireEvent.click(screen.getByText(/track #2 → id-7/))
    expect(screen.getByText(/Candidate comparison/)).toBeInTheDocument()
    expect(screen.getByText('id-7 ✓')).toBeInTheDocument()
    expect(screen.getByText('id-3')).toBeInTheDocument()
    expect(screen.getByText('0.93')).toBeInTheDocument()
  })

  it('falls back to direct row rendering without candidates', () => {
    renderPanel([baseEvent])
    fireEvent.click(screen.getByText(/track #2 → id-7/))
    expect(screen.getByText(/No competing candidates recorded/)).toBeInTheDocument()
  })
})
