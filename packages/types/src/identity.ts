import type { BoundingBox } from './common'

export interface IdentityObservationMeta {
  frameId: number
  timestampSec: number
  bbox: BoundingBox
  confidence: number
  occlusionLevel: number
  qualityScore: number
  embedding: number[] | null
}

export interface IdentityPrototype {
  id: string
  identityId: string
  embedding: number[]
  qualityScore: number
  observationCount: number
  lastUpdatedFrame: number
  createdAt: string
  updatedAt: string
}

export interface Identity {
  id: string
  videoId: string
  colorHex: string
  firstSeenFrame: number
  lastSeenFrame: number
  observationCount: number
  occlusionCount: number
  maxOcclusionDurationSec: number
  recoveries: number
  averageConfidence: number
  prototype: IdentityPrototype | null
  observations: IdentityObservationMeta[]
  trajectory: Array<{ frameId: number; x: number; y: number }>
}

export interface IdentityListResponse {
  identities: Identity[]
  total: number
}

export interface ReIdentificationEvent {
  id: string
  videoId: string
  trackId: string
  identityId: string
  disappearanceFrame: number
  reappearanceFrame: number
  occlusionDurationSec: number
  similarityScore: number
  confidence: number
  decision: 'accepted' | 'rejected'
  candidateIdentityIds: string[]
  candidateScores: Record<string, number>
}

export interface ReIdentificationListResponse {
  events: ReIdentificationEvent[]
  lostTracks: LostTrackInfo[]
  total: number
}

export interface LostTrackInfo {
  trackId: string
  identityId: string | null
  lostAtFrame: number
  occlusionDurationSec: number
  visibilityState: string
}