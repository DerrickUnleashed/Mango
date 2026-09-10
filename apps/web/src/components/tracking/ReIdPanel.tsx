import type { PersistedReidEvent } from '@orchardvision/types'
import { useReidEvents } from '../../hooks/useVideos'

interface ReIdPanelProps {
  videoId: string
  enabled: boolean
}

export function ReIdPanel({ videoId, enabled }: ReIdPanelProps) {
  const { data, isLoading, isError } = useReidEvents(videoId, enabled)
  const events = data?.events ?? []

  if (!enabled) return null

  if (isLoading) {
    return (
      <div className="flex h-40 items-center justify-center rounded-xl border border-surface-800 bg-surface-950">
        <span className="text-sm text-surface-500">Loading re-identification events…</span>
      </div>
    )
  }

  if (isError) {
    return (
      <div className="rounded-xl border border-surface-800 bg-surface-950 p-5 text-sm text-red-400">
        Failed to load re-identification data.
      </div>
    )
  }

  if (!events.length) {
    return (
      <div className="flex h-40 items-center justify-center rounded-xl border border-surface-800 bg-surface-950">
        <p className="text-sm text-surface-500">
          No re-identifications in this run — fruits stayed visible throughout.
        </p>
      </div>
    )
  }

  const accepted = events.filter((e) => e.accepted).length

  return (
    <div className="rounded-xl border border-surface-800 bg-surface-950">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-surface-800 px-4 py-3">
        <div>
          <h2 className="font-medium text-surface-200">Re-identifications</h2>
          <p className="text-xs text-surface-500">
            {events.length} event{events.length === 1 ? '' : 's'} · {accepted} accepted
          </p>
        </div>
      </div>
      <ul className="max-h-80 overflow-y-auto p-2">
        {events.map((event) => (
          <ReIdRow key={event.id} event={event} />
        ))}
      </ul>
    </div>
  )
}

function ReIdRow({ event }: { event: PersistedReidEvent }) {
  const gapFrames = event.reappearanceFrameId - event.lostFrameId
  return (
    <li>
      <div className="flex w-full flex-wrap items-center justify-between gap-2 rounded-lg px-3 py-2 transition-colors hover:bg-surface-900">
        <span className="flex items-center gap-2">
          <span
            className={`h-2.5 w-2.5 rounded-full ${
              event.accepted ? 'bg-orchard-400' : 'bg-red-400'
            }`}
          />
          <span className="font-mono text-sm text-surface-200">
            track #{event.trackId} → id-{event.identityId}
          </span>
          {event.accepted && (
            <span className="rounded-full bg-orchard-600/20 px-2 py-0.5 text-[10px] font-medium text-orchard-300">
              recovered
            </span>
          )}
        </span>
        <span className="text-xs text-surface-500">
          lost f{event.lostFrameId} · {gapFrames}f gap · sim {event.similarity.toFixed(2)}
        </span>
      </div>
    </li>
  )
}
