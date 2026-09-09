import type { BoundingBox, VisibilityState } from './common'

export interface Detection {
  id: string
  videoId: string
  frameId: number
  trackId: string | null
  identityId: string | null
  bbox: BoundingBox
  confidence: number
  classLabel: string
  isLowConfidence: boolean
}

export interface DetectionsByFrame {
  frameId: number
  detections: Detection[]
}

export interface TrackObservation {
  frameId: number
  bbox: BoundingBox
  confidence: number
  centerX: number
  centerY: number
  visibilityState: VisibilityState
  isOccluded: boolean
  embedding: number[] | null
}

export interface Track {
  id: string
  videoId: string
  shortId: number
  identityId: string | null
  firstFrame: number
  lastFrame: number
  totalObservations: number
  status: 'active' | 'lost' | 'removed'
  visibilityState: VisibilityState
  averageConfidence: number
  observation: TrackObservation[]
  bbox: BoundingBox | null
}

export interface TrackListResponse {
  tracks: Track[]
  total: number
}

export interface PersistedTrackPoint {
  frameId: number
  bbox: [number, number, number, number]
  confidence: number
  isOccluded: boolean
}

export interface PersistedTrack {
  id: string
  jobId: string
  videoId: string
  trackId: number
  status: 'active' | 'lost'
  points: PersistedTrackPoint[]
  createdAt: string | null
}

export interface PersistedTrackListResponse {
  tracks: PersistedTrack[]
  total: number
}

export interface PersistedDetection {
  id: string
  videoId: string
  frameId: number
  trackId: number | null
  bbox: [number, number, number, number]
  confidence: number
  classLabel: string
  isOccluded: boolean
}

export interface PersistedDetectionListResponse {
  detections: PersistedDetection[]
  total: number
}