import type { BoundingBox } from "./common";

export interface IdentityObservationMeta {
  frameId: number;
  timestampSec: number;
  bbox: BoundingBox;
  confidence: number;
  occlusionLevel: number;
  qualityScore: number;
  embedding: number[] | null;
}

export interface IdentityPrototype {
  id: string;
  identityId: string;
  embedding: number[];
  qualityScore: number;
  observationCount: number;
  lastUpdatedFrame: number;
  createdAt: string;
  updatedAt: string;
}

export interface Identity {
  id: string;
  videoId: string;
  colorHex: string;
  firstSeenFrame: number;
  lastSeenFrame: number;
  observationCount: number;
  occlusionCount: number;
  maxOcclusionDurationSec: number;
  recoveries: number;
  averageConfidence: number;
  prototype: IdentityPrototype | null;
  observations: IdentityObservationMeta[];
  trajectory: Array<{ frameId: number; x: number; y: number }>;
}

export interface IdentityListResponse {
  identities: Identity[];
  total: number;
}

export interface PersistedIdentity {
  id: string;
  videoId: string;
  identityId: number;
  quality: number;
  observationCount: number;
  firstFrameId: number;
  lastFrameId: number;
  lastTrackId: number | null;
  isConfident: boolean;
  prototype: number[];
  createdAt: string | null;
}

export interface PersistedIdentityListResponse {
  identities: PersistedIdentity[];
  total: number;
}

export interface IdentityProjectionPoint {
  x: number;
  y: number;
  identityId: number;
  quality: number;
  observationCount: number;
  isConfident: boolean;
}

export interface IdentityProjectionResponse {
  points: IdentityProjectionPoint[];
  method: "tsne" | "pca" | "umap";
  total: number;
}

export interface ObservationProjectionPoint {
  x: number;
  y: number;
  identityId: number;
  frameId: number;
  trackId: number | null;
  bbox: [number, number, number, number] | null;
  confidence: number;
  isOccluded: boolean;
}

export interface ObservationProjectionResponse {
  points: ObservationProjectionPoint[];
  method: "tsne" | "pca" | "umap";
  total: number;
}

export interface PersistedIdentityObservation {
  id: string;
  videoId: string;
  identityId: number;
  frameId: number;
  trackId: number | null;
  bbox: [number, number, number, number];
  confidence: number;
  isOccluded: boolean;
  qualityAfter: number | null;
}

export interface PersistedObservationListResponse {
  observations: PersistedIdentityObservation[];
  total: number;
}

export interface PersistedReidEvent {
  id: string
  videoId: string
  trackId: number
  victimTrackId: number
  identityId: number
  lostFrameId: number
  reappearanceFrameId: number
  similarity: number
  confidence: number
  accepted: boolean
  candidateIdentityIds?: number[]
  candidateScores?: Record<string, number>
  createdAt: string | null
}

export interface PersistedReidListResponse {
  events: PersistedReidEvent[];
  total: number;
}

export interface ReIdentificationEvent {
  id: string;
  videoId: string;
  trackId: string;
  identityId: string;
  disappearanceFrame: number;
  reappearanceFrame: number;
  occlusionDurationSec: number;
  similarityScore: number;
  confidence: number;
  decision: "accepted" | "rejected";
  candidateIdentityIds: string[];
  candidateScores: Record<string, number>;
}

export interface ReIdentificationListResponse {
  events: ReIdentificationEvent[];
  lostTracks: LostTrackInfo[];
  total: number;
}

export interface LostTrackInfo {
  trackId: string;
  identityId: string | null;
  lostAtFrame: number;
  occlusionDurationSec: number;
  visibilityState: string;
}
