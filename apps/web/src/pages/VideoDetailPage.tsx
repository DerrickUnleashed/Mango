import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useProcessVideo, useVideo } from '../hooks/useVideos'
import { useToast } from '../components/ui/useToast'
import { TrackVisualizer } from '../components/tracking/TrackVisualizer'

export function VideoDetailPage() {
  const { videoId = '' } = useParams()
  const { push } = useToast()
  const video = useVideo(videoId)
  const process = useProcessVideo()
  const [tracker, setTracker] = useState<'mock' | 'bytetrack'>('mock')

  const job = video.data?.processingJob ?? null
  const isProcessing = job?.status === 'running' || job?.status === 'queued'

  function startProcessing() {
    process.mutate(
      { videoId, request: { inferenceMode: 'mock', tracker } },
      {
        onSuccess: () => push('Processing started', 'success'),
        onError: (err) => push(`Failed to start: ${err.message}`, 'error'),
      },
    )
  }

  if (video.isLoading) {
    return (
      <div className="flex h-full items-center justify-center" role="status">
        <span className="text-surface-500">Loading…</span>
      </div>
    )
  }

  if (video.isError || !video.data) {
    return (
      <div className="space-y-2" role="alert">
        <h1 className="text-xl font-semibold text-red-400">Failed to load video</h1>
        <p className="text-sm text-surface-400">Check the API and try again.</p>
      </div>
    )
  }

  const v = video.data

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-surface-50">{v.originalName}</h1>
        <p className="mt-1 text-sm text-surface-400">
          {v.width && v.height ? `${v.width}×${v.height} · ` : ''}
          {v.fps ? `${v.fps.toFixed(1)} fps · ` : ''}
          {v.frameCount ? `${v.frameCount} frames · ` : ''}
          {v.durationSeconds ? `${v.durationSeconds.toFixed(1)}s` : ''}
        </p>
      </div>

      {/* Tracking visualization — shown once the video has been processed */}
      {v.status === 'processed' && v.width && v.height && v.frameCount && (
        <TrackVisualizer
          videoId={v.id}
          width={v.width}
          height={v.height}
          frameCount={v.frameCount}
          enabled
        />
      )}

      {/* Preview area — frame visualization will be implemented in a later phase */}
      <div className="flex aspect-video items-center justify-center rounded-xl border border-surface-800 bg-surface-950">
        <div className="text-center">
          <span className="text-4xl" aria-hidden="true">🎥</span>
          <p className="mt-2 text-sm text-surface-500">
            Video preview {v.status === 'processed' ? '(track overlay above)' : ''}
          </p>
        </div>
      </div>

      {/* Processing controls */}
      <div className="rounded-xl border border-surface-800 bg-surface-900/60 p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="font-medium text-surface-200">Processing</h2>
            <p className="mt-1 text-sm text-surface-400">
              {job
                ? `Status: ${job.status} · ${job.stage} · ${Math.round(job.progress)}%`
                : 'Run the analysis pipeline to detect, track, and re-identify fruits.'}
            </p>
            {job?.error && <p className="mt-1 text-sm text-red-400">Error: {job.error}</p>}
          </div>
          <div className="flex items-center gap-2">
            <label
              className="text-xs font-medium text-surface-400"
              htmlFor="tracker-select"
              title="Re-run processing with the selected tracker"
            >
              Tracker
            </label>
            <select
              id="tracker-select"
              value={tracker}
              onChange={(e) => setTracker(e.target.value as 'mock' | 'bytetrack')}
              disabled={isProcessing || process.isPending}
              className="rounded-lg border border-surface-700 bg-surface-900 px-3 py-2 text-sm text-surface-200 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-orchard-400 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <option value="mock">Mock</option>
              <option value="bytetrack">ByteTrack</option>
            </select>
          </div>
          <button
            type="button"
            onClick={startProcessing}
            disabled={isProcessing || process.isPending}
            className="rounded-lg bg-orchard-600 px-4 py-2 font-medium text-white transition-colors hover:bg-orchard-500 disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-orchard-400"
          >
            {isProcessing ? 'Processing…' : 'Start Processing'}
          </button>
        </div>
        {isProcessing && (
          <div
            className="mt-4 h-1.5 overflow-hidden rounded-full bg-surface-800"
            role="progressbar"
            aria-valuenow={job?.progress ?? 0}
            aria-valuemin={0}
            aria-valuemax={100}
          >
            <div
              className="h-full rounded-full bg-orchard-500 transition-all"
              style={{ width: `${job?.progress ?? 0}%` }}
            />
          </div>
        )}
      </div>
    </div>
  )
}