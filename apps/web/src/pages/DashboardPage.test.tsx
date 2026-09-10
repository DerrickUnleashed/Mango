import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import type { Video } from '@orchardvision/types'
import { DashboardPage } from './DashboardPage'

const navigate = vi.fn()

vi.mock('react-router-dom', () => ({
  useNavigate: () => navigate,
}))

const mocks = vi.hoisted(() => {
  const video: Video = {
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
    processingJob: null,
  }
  return { video, empty: false }
})

vi.mock('../hooks/useVideos', () => ({
  useVideos: () => ({
    data: mocks.empty ? { videos: [], total: 0 } : { videos: [mocks.video], total: 1 },
    isLoading: false,
    isError: false,
  }),
  useHealth: () => ({ isSuccess: true }),
}))

describe('DashboardPage', () => {
  it('shows stats and the video library', () => {
    mocks.empty = false
    render(<DashboardPage />)
    expect(screen.getByRole('heading', { name: 'Dashboard' })).toBeInTheDocument()
    expect(screen.getByText('API connected')).toBeInTheDocument()
    expect(screen.getByText('Total Videos')).toBeInTheDocument()
    expect(screen.getByText('Orchard A.mp4')).toBeInTheDocument()
  })

  it('shows an empty library state without videos', () => {
    mocks.empty = true
    render(<DashboardPage />)
    expect(screen.getByText('No videos uploaded yet.')).toBeInTheDocument()
    expect(screen.getByText('Total Videos')).toBeInTheDocument()
  })

  it('navigates to a video from the library', () => {
    mocks.empty = false
    render(<DashboardPage />)
    screen.getByRole('button', { name: /Orchard A\.mp4/ }).click()
    expect(navigate).toHaveBeenCalledWith('/videos/vid-1')
  })
})
