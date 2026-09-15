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
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-display text-2xl font-semibold text-surface-50">Dashboard</h1>
          <p className="mt-1 text-sm text-surface-400">
            Long-term fruit tracking and counting platform for mango orchards
          </p>
        </div>
        <div className="glass flex items-center gap-2 rounded-full px-3 py-1.5" aria-live="polite">
          <span
            className={`h-2 w-2 rounded-full ${health.isSuccess ? 'bg-emerald-400' : 'bg-surface-600'}`}
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
        <StatCard label="Identity Recovery" value="—" accent="warning" hint="Processing required" />
      </div>

      <div className="glass card-glow rounded-2xl p-6">
        <div className="flex items-center justify-between">
          <h2 className="font-display text-sm font-semibold text-surface-200">Library</h2>
          <button
            type="button"
            onClick={() => navigate('/videos')}
            className="cursor-pointer rounded-full border border-orchard-700/60 bg-orchard-500/10 px-3 py-1 text-xs font-medium text-orchard-300 transition-colors hover:bg-orchard-500/20"
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
            Failed to load videos. Is the API running on port 8001?
          </p>
        ) : (videos.data?.videos.length ?? 0) === 0 ? (
          <div className="mt-6 text-center">
            <p className="text-surface-400">No videos uploaded yet.</p>
            <button
              type="button"
              onClick={() => navigate('/videos')}
              className="bg-mango mt-3 cursor-pointer rounded-full px-5 py-2 text-sm font-semibold text-surface-950 shadow-[0_8px_24px_-8px_rgba(249,115,22,0.6)] transition-transform hover:scale-[1.03] active:scale-[0.98]"
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
                  className="glass-soft card-glow flex w-full cursor-pointer items-center justify-between rounded-xl px-4 py-3 text-left transition-colors hover:border-orchard-500/40"
                >
                  <span className="flex min-w-0 items-center gap-3">
                    <span className="bg-mango flex h-8 w-8 shrink-0 items-center justify-center rounded-lg opacity-90">
                      <svg
                        className="h-4 w-4 text-surface-950"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1.8"
                        strokeLinecap="round"
                        aria-hidden="true"
                      >
                        <path d="M7 3h10a4 4 0 0 1 4 4v10a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4V7a4 4 0 0 1 4-4zM3 8h18M3 16h18M8 8v13M16 8v13" />
                      </svg>
                    </span>
                    <span className="truncate font-medium text-surface-200">
                      {video.originalName}
                    </span>
                  </span>
                  <span className="ml-4 shrink-0 rounded-full border border-surface-700/60 bg-surface-800/50 px-2.5 py-0.5 text-xs text-surface-400">
                    {video.status}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="glass-soft flex items-center justify-between rounded-2xl px-5 py-4">
        <div className="flex items-center gap-3">
          <span className="bg-mango-soft flex h-9 w-9 items-center justify-center rounded-xl text-orchard-300">
            <svg
              className="h-5 w-5"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9L12 3z" />
            </svg>
          </span>
          <div>
            <p className="text-sm font-medium text-surface-100">Pipeline ready</p>
            <p className="text-xs text-surface-500">
              Upload a video and run detection, tracking, and re-identification end-to-end.
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={() => navigate('/videos')}
          className="bg-mango shrink-0 cursor-pointer rounded-full px-4 py-2 text-xs font-semibold text-surface-950 transition-transform hover:scale-[1.03] active:scale-[0.98]"
        >
          Get started
        </button>
      </div>
    </div>
  )
}
