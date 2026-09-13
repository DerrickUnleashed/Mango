import { useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useProcessVideo, useVideo } from '../hooks/useVideos'
import { useSettings } from '../hooks/useSettings'
import { useToast } from '../components/ui/useToast'
import { videoFileUrl } from '../api/videos'
import { AnalyticsPanel } from '../components/tracking/AnalyticsPanel'
import { IdentitiesPanel } from '../components/tracking/IdentitiesPanel'
import { MotionPanel } from '../components/tracking/MotionPanel'
import { ReIdPanel } from '../components/tracking/ReIdPanel'
import { TrackVisualizer } from '../components/tracking/TrackVisualizer'
import { VideoTrackingOverlay } from '../components/tracking/VideoTrackingOverlay'

export function VideoDetailPage() {
  const { videoId = '' } = useParams()
  const { push } = useToast()
  const video = useVideo(videoId)
  const process = useProcessVideo()
  const settings = useSettings()
  const [inferenceMode, setInferenceMode] = useState<'mock' | 'real'>('real')
  const [tracker, setTracker] = useState<'mock' | 'bytetrack'>('mock')
  const [cameraMotion, setCameraMotion] = useState<'static' | 'drift'>('static')
  const videoRef = useRef<HTMLVideoElement | null>(null)

  const job = video.data?.processingJob ?? null
  const isProcessing = job?.status === 'running' || job?.status === 'queued'

  const configEntries: Array<[string, string]> = job?.config
    ? [
        ['Inference', job.config.inference_mode],
        ['Confidence', job.config.confidence_threshold.toFixed(2)],
        ['Tracker', job.config.tracker],
        ['Camera', job.config.camera_motion],
        ['Re-ID threshold', job.config.reid_threshold.toFixed(2)],
        ['Memory update rate', job.config.memory_update_rate.toFixed(2)],
        ...(job.config.max_frames != null
          ? [['Max frames', String(job.config.max_frames)] as [string, string]]
          : []),
      ]
    : []

  function startProcessing() {
    process.mutate(
      { videoId, request: { inferenceMode, tracker, cameraMotion } },
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
  const prefs = settings.data?.values

  function seekToFrame(frameId: number) {
    const player = videoRef.current
    if (!player || !v.fps) return
    player.currentTime = frameId / v.fps
  }

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
      {v.status === 'processed' &&
        (prefs?.showTrackVisualizer ?? true) &&
        v.width &&
        v.height &&
        v.frameCount && (
          <TrackVisualizer
            videoId={v.id}
            width={v.width}
            height={v.height}
            frameCount={v.frameCount}
            enabled
          />
        )}

      {/* Learned identities — shown once the video has been processed */}
      {v.status === 'processed' && (prefs?.showIdentitiesPanel ?? true) && (
        <IdentitiesPanel videoId={v.id} enabled seekToFrame={seekToFrame} />
      )}

      {/* Re-identification recoveries — shown once the video has been processed */}
      {v.status === 'processed' && (prefs?.showReidPanel ?? true) && (
        <ReIdPanel videoId={v.id} enabled />
      )}

      {/* Camera motion estimate — shown once the video has been processed */}
      {v.status === 'processed' && (prefs?.showMotionPanel ?? true) && (
        <MotionPanel videoId={v.id} enabled />
      )}

      {/* Aggregated analytics — shown once the video has been processed */}
      {v.status === 'processed' && (prefs?.showAnalyticsPanel ?? true) && (
        <AnalyticsPanel videoId={v.id} enabled />
      )}

      {/* Preview area — plays the uploaded source; the track overlay above
          mirrors the processed run */}
      <div className="relative overflow-hidden rounded-xl border border-surface-800 bg-surface-950">
        <video
          ref={videoRef}
          src={videoFileUrl(v.id)}
          controls
          playsInline
          preload="metadata"
          className="block aspect-video w-full bg-black"
          aria-label={`Video preview for ${v.originalName}`}
        >
          <track kind="captions" />
        </video>
        {v.status === 'processed' && v.width && v.height && v.frameCount && (
          <VideoTrackingOverlay
            videoId={v.id}
            videoRef={videoRef}
            width={v.width}
            height={v.height}
            frameCount={v.frameCount}
            fps={v.fps ?? 30}
            enabled
          />
        )}
      </div>

      {/* Processing controls */}
      <div className="rounded-xl border border-surface-800 bg-surface-900/60 p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="font-medium text-surface-200">Processing</h2>
            <p className="mt-1 text-sm text-surface-400">
              {job
                ? `Status: ${job.status}${job.message ? ` · ${job.message}` : ''} · ${job.stage} · ${Math.round(job.progress)}%`
                : 'Run the analysis pipeline to detect, track, and re-identify fruits.'}
            </p>
            {job?.error && <p className="mt-1 text-sm text-red-400">Error: {job.error}</p>}
            {configEntries.length > 0 && (
              <dl className="mt-3 flex flex-wrap gap-2" aria-label="Pipeline configuration">
                {configEntries.map(([label, value]) => (
                  <div
                    key={label}
                    className="rounded-md border border-surface-800 bg-surface-950 px-2 py-1 text-xs text-surface-400"
                  >
                    <dt className="inline text-surface-500">{label}</dt>
                    {` · `}
                    <dd className="inline text-surface-200">{value}</dd>
                  </div>
                ))}
              </dl>
            )}
          </div>
          <div className="flex items-center gap-2">
            <label
              className="text-xs font-medium text-surface-400"
              htmlFor="inference-select"
              title="Mock uses a synthetic detector; Real runs the saved YOLO weights"
            >
              Inference
            </label>
            <select
              id="inference-select"
              value={inferenceMode}
              onChange={(e) => setInferenceMode(e.target.value as 'mock' | 'real')}
              disabled={isProcessing || process.isPending}
              className="rounded-lg border border-surface-700 bg-surface-900 px-3 py-2 text-sm text-surface-200 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-orchard-400 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <option value="mock">Mock</option>
              <option value="real">Real</option>
            </select>
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
          <div className="flex items-center gap-2">
            <label
              className="text-xs font-medium text-surface-400"
              htmlFor="motion-select"
              title="Simulate a drifting camera and stabilize tracks via motion compensation"
            >
              Camera
            </label>
            <select
              id="motion-select"
              value={cameraMotion}
              onChange={(e) => setCameraMotion(e.target.value as 'static' | 'drift')}
              disabled={isProcessing || process.isPending}
              className="rounded-lg border border-surface-700 bg-surface-900 px-3 py-2 text-sm text-surface-200 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-orchard-400 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <option value="static">Static</option>
              <option value="drift">Drift</option>
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
