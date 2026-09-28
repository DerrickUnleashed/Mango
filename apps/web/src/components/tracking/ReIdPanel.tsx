import { useState } from 'react'
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
      <div className="flex h-40 items-center justify-center clay clay-lift rounded-2xl">
        <span className="text-sm text-surface-500">Loading re-identification events…</span>
      </div>
    )
  }

  if (isError) {
    return (
      <div className="clay clay-lift rounded-2xl p-5 text-sm text-red-400">
        Failed to load re-identification data.
      </div>
    )
  }

  if (!events.length) {
    return (
      <div className="flex h-40 items-center justify-center clay clay-lift rounded-2xl">
        <p className="text-sm text-surface-500">
          No re-identifications in this run — fruits stayed visible throughout.
        </p>
      </div>
    )
  }

  const accepted = events.filter((e) => e.accepted).length

  return (
    <div className="clay clay-lift rounded-2xl">
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

export function CandidateComparison({ event }: { event: PersistedReidEvent }) {
  const candidateIds = event.candidateIdentityIds ?? []
  const scores = event.candidateScores ?? {}
  if (candidateIds.length === 0 || Object.keys(scores).length === 0) {
    return <p className="px-1 pb-1 text-xs text-surface-500">No competing candidates recorded.</p>
  }

  const maxScore = Math.max(1, ...objectValues(scores))
  return (
    <div className="mb-2 ml-6 clay-inset-sm rounded-lg px-3 py-2">
      <p className="mb-2 text-xs font-medium text-surface-400">Candidate comparison</p>
      <ul className="space-y-1.5">
        {candidateIds.map((candidateId) => {
          const score = scores[String(candidateId)] ?? 0
          const isAccepted = candidateId === event.identityId
          return (
            <li key={candidateId} className="flex items-center gap-2">
              <span
                className={`w-12 flex-shrink-0 font-mono text-[11px] ${
                  isAccepted ? 'font-semibold text-orchard-300' : 'text-surface-500'
                }`}
              >
                id-{candidateId}
                {isAccepted ? ' ✓' : ''}
              </span>
              <div className="h-2.5 flex-1 overflow-hidden rounded bg-surface-800">
                <div
                  className="h-full rounded"
                  style={{
                    width: `${Math.min(100, (score / maxScore) * 100)}%`,
                    backgroundColor: isAccepted ? '#f59e0b' : '#475569',
                  }}
                />
              </div>
              <span className="w-10 flex-shrink-0 text-right font-mono text-[11px] text-surface-400">
                {score.toFixed(2)}
              </span>
            </li>
          )
        })}
      </ul>
    </div>
  )
}

function objectValues(record: Record<string, number>): number[] {
  return Object.values(record)
}

function ReIdRow({ event }: { event: PersistedReidEvent }) {
  const [open, setOpen] = useState(false)
  const gapFrames = event.reappearanceFrameId - event.lostFrameId
  return (
    <li>
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="flex w-full flex-wrap items-center justify-between gap-2 rounded-lg px-3 py-2 text-left transition-colors hover:bg-surface-900"
        aria-expanded={open}
      >
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
      </button>
      {open && <CandidateComparison event={event} />}
    </li>
  )
}
