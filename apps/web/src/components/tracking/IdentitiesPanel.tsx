import { useState } from 'react'
import type { PersistedIdentity, PersistedIdentityObservation } from '@orchardvision/types'
import { useIdentities, useIdentityObservations } from '../../hooks/useVideos'
import { videoFrameUrl } from '../../api/videos'
import { EmbeddingMap } from './EmbeddingMap'
import { colorForIdentity } from './identityColors'

interface IdentitiesPanelProps {
  videoId: string
  enabled: boolean
}

export function IdentitiesPanel({ videoId, enabled }: IdentitiesPanelProps) {
  const [showMap, setShowMap] = useState(false)
  const { data, isLoading, isError } = useIdentities(videoId, enabled)
  const identities = data?.identities ?? []

  if (!enabled) return null

  if (isLoading) {
    return (
      <div className="flex h-40 items-center justify-center clay clay-lift rounded-2xl">
        <span className="text-sm text-surface-500">Loading identities…</span>
      </div>
    )
  }

  if (isError) {
    return (
      <div className="clay clay-lift rounded-2xl p-5 text-sm text-red-400">
        Failed to load identity data.
      </div>
    )
  }

  if (!identities.length) {
    return (
      <div className="flex h-40 items-center justify-center clay clay-lift rounded-2xl">
        <p className="text-sm text-surface-500">Run processing to generate identities.</p>
      </div>
    )
  }

  const confident = identities.filter((i) => i.isConfident).length

  return (
    <div className="clay clay-lift rounded-2xl">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-surface-800 px-4 py-3">
        <div>
          <h2 className="font-medium text-surface-200">Identities</h2>
          <p className="text-xs text-surface-500">
            {identities.length} identity{identities.length === 1 ? '' : 's'} · {confident} confident
          </p>
        </div>
        <button
          type="button"
          onClick={() => setShowMap((value) => !value)}
          className="rounded-md border border-surface-700 px-2.5 py-1 text-xs text-surface-300 transition-colors hover:bg-surface-800"
          aria-pressed={showMap}
        >
          {showMap ? 'Hide map' : 'Embedding map'}
        </button>
      </div>
      {showMap && (
        <div className="border-b border-surface-800 p-3">
          <EmbeddingMap videoId={videoId} enabled={enabled} />
        </div>
      )}
      <ul className="max-h-72 overflow-y-auto p-2">
        {identities.map((identity) => (
          <IdentityRow key={identity.id} identity={identity} videoId={videoId} />
        ))}
      </ul>
    </div>
  )
}

function representativeFrames(
  observations: PersistedIdentityObservation[],
): PersistedIdentityObservation[] {
  if (observations.length === 0) return []
  const byConfidence = [...observations].sort((a, b) => b.confidence - a.confidence)
  const picks = [observations[0], byConfidence[0], observations[observations.length - 1]]
  const seen = new Set<number>()
  const unique: PersistedIdentityObservation[] = []
  for (const obs of picks) {
    if (!seen.has(obs.frameId)) {
      seen.add(obs.frameId)
      unique.push(obs)
    }
  }
  return unique.slice(0, 3)
}

function RepresentativeStrip({
  videoId,
  observations,
}: {
  videoId: string
  observations: PersistedIdentityObservation[]
}) {
  const frames = representativeFrames(observations)
  return (
    <div className="mb-2 flex gap-2">
      {frames.map((obs) => (
        <figure key={obs.frameId} className="min-w-0">
          <img
            src={videoFrameUrl(videoId, obs.frameId, 160)}
            alt={`Representative frame ${obs.frameId}`}
            loading="lazy"
            className="h-16 w-28 rounded-md border border-surface-800 object-cover"
          />
          <figcaption className="mt-0.5 text-center font-mono text-[10px] text-surface-500">
            f{obs.frameId} · {obs.confidence.toFixed(2)}
          </figcaption>
        </figure>
      ))}
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
            style={{ backgroundColor: colorForIdentity(identity.identityId) }}
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
        <div className="mb-2 ml-6 clay-inset-sm rounded-lg px-3 py-2">
          {observations.isLoading && (
            <p className="text-xs text-surface-500">Loading observations…</p>
          )}
          {obs.length > 0 && <RepresentativeStrip videoId={videoId} observations={obs} />}
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
