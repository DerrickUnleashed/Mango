import type { PersistedIdentity } from '@orchardvision/types'
import { useIdentities } from '../../hooks/useVideos'

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
            {identities.length} identity{identities.length === 1 ? '' : 's'} ·{' '}
            {confident} confident
          </p>
        </div>
      </div>
      <ul className="max-h-72 overflow-y-auto p-2">
        {identities.map((identity) => (
          <IdentityRow key={identity.id} identity={identity} />
        ))}
      </ul>
    </div>
  )
}

function IdentityRow({ identity }: { identity: PersistedIdentity }) {
  return (
    <li>
      <div className="flex w-full items-center justify-between gap-2 rounded-lg px-3 py-2 transition-colors hover:bg-surface-900">
        <span className="flex items-center gap-2">
          <span
            className="h-2.5 w-2.5 rounded-full"
            style={{ backgroundColor: colorFor(identity.identityId) }}
          />
          <span className="font-mono text-sm text-surface-200">
            id-{identity.identityId}
          </span>
          {identity.isConfident && (
            <span className="rounded-full bg-orchard-600/20 px-2 py-0.5 text-[10px] font-medium text-orchard-300">
              confident
            </span>
          )}
        </span>
        <span className="text-xs text-surface-500">
          {identity.firstFrameId}–{identity.lastFrameId} ·{' '}
          {identity.observationCount} obs · q {identity.quality.toFixed(2)}
        </span>
      </div>
    </li>
  )
}