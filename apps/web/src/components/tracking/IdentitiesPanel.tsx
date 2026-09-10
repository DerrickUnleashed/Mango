import { useState } from 'react'
import type { PersistedIdentity } from '@orchardvision/types'
import { useIdentities, useIdentityObservations } from '../../hooks/useVideos'

const PALETTE = [
  '#f59e0b',
  '#22d3ee',
  '#a78bfa',
  '#34d399',
  '#fb7185',
  '#60a5fa',
  '#facc15',
  '#f472b6',
  '#4ade80',
  '#fb923c',
]

function colorFor(identityId: number): string {
  return PALETTE[identityId % PALETTE.length]
}

interface IdentitiesPanelProps {
  videoId: string
  enabled: boolean
}

export function IdentitiesPanel({ videoId, enabled }: IdentitiesPanelProps) {
  const { data, isLoading, isError } = useIdentities(videoId, enabled)
  const identities = data?.identities ?? []

  if (!enabled) return null

  if (isLoading) {
    return (
      <div className="flex h-40 items-center justify-center rounded-xl border border-surface-800 bg-surface-950">
        <span className="text-sm text-surface-500">Loading identities…</span>
      </div>
    )
  }

  if (isError) {
    return (
      <div className="rounded-xl border border-surface-800 bg-surface-950 p-5 text-sm text-red-400">
        Failed to load identity data.
      </div>
    )
  }

  if (!identities.length) {
    return (
      <div className="flex h-40 items-center justify-center rounded-xl border border-surface-800 bg-surface-950">
        <p className="text-sm text-surface-500">Run processing to generate identities.</p>
      </div>
    )
  }

  const confident = identities.filter((i) => i.isConfident).length

  return (
    <div className="rounded-xl border border-surface-800 bg-surface-950">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-surface-800 px-4 py-3">
        <div>
          <h2 className="font-medium text-surface-200">Identities</h2>
          <p className="text-xs text-surface-500">
            {identities.length} identity{identities.length === 1 ? '' : 's'} · {confident} confident
          </p>
        </div>
      </div>
      <ul className="max-h-72 overflow-y-auto p-2">
        {identities.map((identity) => (
          <IdentityRow key={identity.id} identity={identity} videoId={videoId} />
        ))}
      </ul>
    </div>
  )
}

function IdentityRow({ identity, videoId }: { identity: PersistedIdentity; videoId: string }) {
  const [open, setOpen] = useState(false)
  const observations = useIdentityObservations(videoId, open ? identity.identityId : null, open)
  const obs = observations.data?.observations ?? []

  return (
    <li>
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="flex w-full items-center justify-between gap-2 rounded-lg px-3 py-2 text-left transition-colors hover:bg-surface-900"
      >
        <span className="flex items-center gap-2">
          <span
            className="h-2.5 w-2.5 rounded-full"
            style={{ backgroundColor: colorFor(identity.identityId) }}
          />
          <span className="font-mono text-sm text-surface-200">id-{identity.identityId}</span>
          {identity.isConfident && (
            <span className="rounded-full bg-orchard-600/20 px-2 py-0.5 text-[10px] font-medium text-orchard-300">
              confident
            </span>
          )}
        </span>
        <span className="text-xs text-surface-500">
          {identity.firstFrameId}–{identity.lastFrameId} · {identity.observationCount} obs · q{' '}
          {identity.quality.toFixed(2)}
        </span>
      </button>

      {open && (
        <div className="mb-2 ml-6 rounded-lg border border-surface-800 bg-surface-900/60 px-3 py-2">
          {observations.isLoading && (
            <p className="text-xs text-surface-500">Loading observations…</p>
          )}
          <ul className="max-h-48 space-y-1 overflow-y-auto">
            {obs.map((observation) => (
              <li
                key={observation.id}
                className="flex items-center justify-between gap-2 rounded px-2 py-0.5 font-mono text-[11px] text-surface-400 hover:bg-surface-800"
              >
                <span className="flex items-center gap-3">
                  <span className="tabular-nums text-surface-300">f{observation.frameId}</span>
                  <span>
                    {observation.trackId === null ? 'no track' : `track ${observation.trackId}`}
                  </span>
                  {observation.isOccluded && (
                    <span className="rounded-full bg-amber-500/15 px-1.5 py-px text-[10px] text-amber-300">
                      occluded
                    </span>
                  )}
                </span>
                <span className="flex items-center gap-3">
                  <span>conf {observation.confidence.toFixed(2)}</span>
                  <span className="tabular-nums text-surface-500">
                    q {observation.qualityAfter?.toFixed(2) ?? '—'}
                  </span>
                </span>
              </li>
            ))}
          </ul>
          {!observations.isLoading && obs.length === 0 && (
            <p className="text-xs text-surface-500">No observations recorded.</p>
          )}
        </div>
      )}
    </li>
  )
}
