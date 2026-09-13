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
          <h1 className="text-2xl font-semibold text-surface-50">Videos</h1>
          <p className="mt-1 text-sm text-surface-400">Upload orchard footage for analysis</p>
        </div>
      </div>

      {/* Upload dropzone */}
      <label
        className={`flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed p-10 text-center transition-colors ${
          upload.isPending
            ? 'border-orchard-700 bg-orchard-950/40'
            : 'border-surface-800 bg-surface-900/40 hover:border-surface-700 hover:bg-surface-900'
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
            <span className="text-2xl" aria-hidden="true">
              Uploading…
            </span>
            <span className="text-sm text-surface-400">
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
                className="h-full rounded-full bg-orchard-500 transition-all"
                style={{ width: `${uploadProgress ?? 0}%` }}
              />
            </div>
          </>
        ) : (
          <>
            <span className="text-sm font-medium text-surface-300">
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
          <div className="rounded-xl border border-surface-800 bg-surface-900/40 p-10 text-center">
            <p className="text-surface-400">No videos yet.</p>
            <p className="mt-1 text-xs text-surface-600">Upload footage above to begin.</p>
          </div>
        ) : (
          <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {(videos.data?.videos ?? []).map((video) => (
              <li key={video.id}>
                <article className="group rounded-xl border border-surface-800 bg-surface-900/60 transition-colors hover:border-surface-700">
                  <div className="flex aspect-video items-center justify-center bg-surface-950">
                    <span className="text-surface-600" aria-hidden="true">
                      🎬
                    </span>
                    <span className="sr-only">Video thumbnail placeholder</span>
                  </div>
                  <div className="p-4">
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
                    <div className="mt-3 flex items-center justify-between">
                      <span className="rounded-full border border-surface-700 px-2 py-0.5 text-xs text-surface-400">
                        {video.status}
                      </span>
                      <div className="flex gap-2">
                        <button
                          type="button"
                          onClick={() => navigate(`/videos/${video.id}`)}
                          className="rounded-md border border-surface-700 px-3 py-1 text-xs font-medium text-surface-300 transition-colors hover:border-surface-500 hover:text-surface-100"
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
                          className="rounded-md border border-surface-800 px-3 py-1 text-xs font-medium text-surface-500 transition-colors hover:border-red-900 hover:text-red-400"
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
