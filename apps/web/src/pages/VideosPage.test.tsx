import { describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import type { Video } from '@orchardvision/types'
import { VideosPage } from './VideosPage'

const navigate = vi.fn()

vi.mock('react-router-dom', () => ({
  useNavigate: () => navigate,
}))

const mocks = vi.hoisted(() => {
  const makeVideo = (id: string, name: string): Video => ({
    id,
    filename: `${id}.mp4`,
    originalName: name,
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
  })
  return {
    push: vi.fn(),
    mutateAsync: vi.fn().mockResolvedValue({ ok: true }),
    makeVideo,
    withVideos: true,
  }
})

vi.mock('../components/ui/useToast', () => ({
  useToast: () => ({ push: mocks.push }),
}))

vi.mock('../hooks/useVideos', () => ({
  useVideos: () => ({
    data: mocks.withVideos
      ? { videos: [mocks.makeVideo('vid-1', 'Orchard A.mp4')], total: 1 }
      : { videos: [], total: 0 },
    isLoading: false,
    isError: false,
  }),
  useUploadVideo: () => ({
    mutate: vi.fn(),
    isPending: false,
    isError: false,
    error: null,
    variables: null,
  }),
  useDeleteVideo: () => ({ mutateAsync: mocks.mutateAsync }),
}))

describe('VideosPage', () => {
  it('lists uploaded videos', () => {
    mocks.withVideos = true
    render(<VideosPage />)
    expect(screen.getByText('Orchard A.mp4')).toBeInTheDocument()
    expect(screen.getByText('Analyze')).toBeInTheDocument()
  })

  it('shows an empty state without videos', () => {
    mocks.withVideos = false
    render(<VideosPage />)
    expect(screen.getByText('No videos yet.')).toBeInTheDocument()
  })

  it('deletes a video after confirmation', async () => {
    mocks.withVideos = true
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true)
    render(<VideosPage />)
    const deleteButton = screen.getAllByText('Delete')[0]
    deleteButton.click()
    await waitFor(() => expect(mocks.mutateAsync).toHaveBeenCalledWith('vid-1'))
    expect(mocks.push).toHaveBeenCalledWith('Video deleted', 'success')
    confirmSpy.mockRestore()
  })
})
