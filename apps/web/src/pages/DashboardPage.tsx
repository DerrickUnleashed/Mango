import { useNavigate } from 'react-router-dom'
import { useHealth, useVideos } from '../hooks/useVideos'
import { StatCard } from '../components/ui/StatCard'

export function DashboardPage() {
  const navigate = useNavigate()
  const videos = useVideos()
  const health = useHealth()

  const totalVideos = videos.data?.total ?? 0

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-surface-50">Dashboard</h1>
          <p className="mt-1 text-sm text-surface-400">
            Long-term fruit tracking and counting platform for mango orchards
          </p>
        </div>
        <div className="flex items-center gap-2" aria-live="polite">
          <span
            className={`h-2 w-2 rounded-full ${health.isSuccess ? 'bg-orchard-400' : 'bg-surface-600'}`}
            aria-hidden="true"
          />
          <span className="text-xs text-surface-400">
            {health.isSuccess ? 'API connected' : 'API offline'}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Total Videos" value={totalVideos} />
        <StatCard label="Fruits Detected" value="—" hint="Upload and process a video" />
        <StatCard label="Unique Identities" value="—" hint="Processing required" />
        <StatCard label="Identity Recovery" value="—" hint="Processing required" />
      </div>

      <div className="rounded-xl border border-surface-800 bg-surface-900/60 p-6">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-surface-200">Library</h2>
          <button
            type="button"
            onClick={() => navigate('/videos')}
            className="text-sm font-medium text-orchard-400 hover:text-orchard-300"
          >
            View all
          </button>
        </div>
        {videos.isLoading ? (
          <p className="mt-4 text-sm text-surface-500" role="status">
            Loading videos…
          </p>
        ) : videos.isError ? (
          <p className="mt-4 text-sm text-red-400" role="alert">
            Failed to load videos. Is the API running on port 8000?
          </p>
        ) : (videos.data?.videos.length ?? 0) === 0 ? (
          <div className="mt-6 text-center">
            <p className="text-surface-400">No videos uploaded yet.</p>
            <button
              type="button"
              onClick={() => navigate('/videos')}
              className="mt-3 rounded-lg bg-orchard-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-orchard-500 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-orchard-400"
            >
              Upload first video
            </button>
          </div>
        ) : (
          <ul className="mt-4 space-y-2">
            {(videos.data?.videos ?? []).slice(0, 5).map((video) => (
              <li key={video.id}>
                <button
                  type="button"
                  onClick={() => navigate(`/videos/${video.id}`)}
                  className="flex w-full items-center justify-between rounded-lg border border-surface-800 bg-surface-900 px-4 py-3 text-left transition-colors hover:border-surface-700 hover:bg-surface-800"
                >
                  <span className="truncate font-medium text-surface-200">
                    {video.originalName}
                  </span>
                  <span className="ml-4 shrink-0 text-xs text-surface-500">{video.status}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
