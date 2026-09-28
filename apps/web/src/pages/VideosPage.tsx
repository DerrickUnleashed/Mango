import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useToast } from '../components/ui/useToast'
import { useDeleteVideo, useUploadVideo, useVideos } from '../hooks/useVideos'
import { ApiError } from '../api/client'

const ACCEPTED_TYPES = [
  'video/mp4',
  'video/quicktime',
  'video/x-msvideo',
  'video/webm',
  'video/mpeg',
]
const MAX_SIZE_BYTES = 2 * 1024 * 1024 * 1024

function FilmIcon({ className = 'h-5 w-5' }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M7 3h10a4 4 0 0 1 4 4v10a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4V7a4 4 0 0 1 4-4zM3 8h18M3 16h18M8 8v13M16 8v13" />
    </svg>
  )
}

function UploadIcon({ className = 'h-5 w-5' }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M12 16V4m0 0l-4 4m4-4l4 4M4 16v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2" />
    </svg>
  )
}

export function VideosPage() {
  const navigate = useNavigate()
  const { push } = useToast()
  const videos = useVideos()
  const [uploadProgress, setUploadProgress] = useState<number | null>(null)
  const upload = useUploadVideo((video) => {
    push(`Video "${video.originalName}" uploaded`, 'success')
    navigate(`/videos/${video.id}`)
  })
  const remove = useDeleteVideo()

  function handleFiles(files: FileList | null) {
    if (!files || files.length === 0) return
    const file = files[0]

    if (!ACCEPTED_TYPES.includes(file.type)) {
      push('Unsupported format. Use MP4, MOV, AVI, WebM, or MPEG.', 'error')
      return
    }
    if (file.size > MAX_SIZE_BYTES) {
      push('File exceeds the 2 GB upload limit.', 'error')
      return
    }
    setUploadProgress(0)
    upload.mutate({ file, onProgress: setUploadProgress })
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-semibold text-surface-50">Videos</h1>
          <p className="mt-1 text-sm text-surface-400">Upload orchard footage for analysis</p>
        </div>
      </div>

      {/* Upload dropzone */}
      <label
        className={`clay-inset-sm flex cursor-pointer flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed p-10 text-center transition-colors ${
          upload.isPending
            ? 'border-orchard-500/70'
            : 'border-surface-700/60 hover:border-orchard-500/60'
        }`}
        role="button"
        aria-label="Upload orchard video"
      >
        <input
          type="file"
          accept={ACCEPTED_TYPES.join(',')}
          className="sr-only"
          onChange={(e) => handleFiles(e.target.files)}
          disabled={upload.isPending}
        />
        {upload.isPending ? (
          <>
            <span className="bg-mango flex h-12 w-12 items-center justify-center rounded-2xl">
              <FilmIcon className="h-6 w-6 text-surface-950" />
            </span>
            <span className="text-sm font-medium text-surface-200">
              {upload.variables?.file.name} — {uploadProgress ?? 0}%
            </span>
            <div
              className="h-1.5 w-56 overflow-hidden rounded-full bg-surface-800"
              role="progressbar"
              aria-valuenow={uploadProgress ?? 0}
              aria-valuemin={0}
              aria-valuemax={100}
            >
              <div
                className="bg-mango h-full rounded-full transition-all"
                style={{ width: `${uploadProgress ?? 0}%` }}
              />
            </div>
          </>
        ) : (
          <>
            <span className="bg-mango-soft flex h-12 w-12 items-center justify-center rounded-2xl text-orchard-300">
              <UploadIcon className="h-6 w-6" />
            </span>
            <span className="text-sm font-medium text-surface-200">
              Drop a video here, or click to browse
            </span>
            <span className="text-xs text-surface-500">MP4, MOV, AVI, WebM, MPEG · up to 2 GB</span>
          </>
        )}
      </label>

      {upload.isError && upload.error instanceof ApiError && (
        <p className="text-sm text-red-400" role="alert">
          Upload failed: {upload.error.message}
        </p>
      )}

      {/* Video list */}
      <section aria-label="Video library" className="space-y-3">
        {videos.isLoading ? (
          <p className="text-sm text-surface-500" role="status">
            Loading videos…
          </p>
        ) : videos.isError ? (
          <p className="text-sm text-red-400" role="alert">
            Failed to load videos. Is the API running on port 8001?
          </p>
        ) : (videos.data?.videos.length ?? 0) === 0 ? (
          <div className="clay clay-lift rounded-2xl p-10 text-center">
            <p className="text-surface-400">No videos yet.</p>
            <p className="mt-1 text-xs text-surface-500">Upload footage above to begin.</p>
          </div>
        ) : (
          <ul className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {(videos.data?.videos ?? []).map((video) => (
              <li key={video.id}>
                <article className="clay clay-lift group flex h-full cursor-pointer flex-col overflow-hidden rounded-2xl">
                  <button
                    type="button"
                    className="flex items-start text-left"
                    onClick={() => navigate(`/videos/${video.id}`)}
                  >
                    <div className="relative flex aspect-video w-full items-center justify-center bg-surface-950/60">
                      <span className="text-surface-500 transition-colors group-hover:text-orchard-300">
                        <FilmIcon className="h-10 w-10" />
                      </span>
                      <span className="sr-only">Video thumbnail placeholder</span>
                    </div>
                  </button>
                  <div className="flex flex-1 flex-col p-4">
                    <h2
                      className="truncate font-medium text-surface-200"
                      title={video.originalName}
                    >
                      {video.originalName}
                    </h2>
                    <p className="mt-1 text-xs text-surface-500">
                      {video.width && video.height ? `${video.width}×${video.height} · ` : ''}
                      {video.fps ? `${video.fps.toFixed(1)} fps` : ''}
                    </p>
                    <div className="mt-3 flex items-center justify-between pt-1">
                      <span className="rounded-full border border-orchard-700/50 bg-orchard-500/10 px-2.5 py-0.5 text-xs text-orchard-300">
                        {video.status}
                      </span>
                      <div className="flex gap-2">
                        <button
                          type="button"
                          onClick={() => navigate(`/videos/${video.id}`)}
                          className="cursor-pointer rounded-lg border border-orchard-700/50 bg-orchard-500/10 px-3 py-1 text-xs font-medium text-orchard-300 transition-colors hover:bg-orchard-500/20"
                        >
                          Analyze
                        </button>
                        <button
                          type="button"
                          onClick={async () => {
                            if (window.confirm(`Delete "${video.originalName}"?`)) {
                              try {
                                await remove.mutateAsync(video.id)
                                push('Video deleted', 'success')
                              } catch {
                                push('Failed to delete video', 'error')
                              }
                            }
                          }}
                          className="cursor-pointer rounded-lg border border-surface-700/60 px-3 py-1 text-xs font-medium text-surface-400 transition-colors hover:border-red-900 hover:text-red-400"
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                  </div>
                </article>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}
