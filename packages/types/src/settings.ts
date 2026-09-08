import type { CameraMotionMode } from './common'

export interface DetectorSettings {
  confidenceThreshold: number
  modelName: string
  inferenceMode: 'mock' | 'real'
}

export interface TrackerSettings {
  matchThreshold: number
  trackBuffer: number
  minTrackLength: number
}

export interface ReIdSettings {
  threshold: number
  maxCandidates: number
  occlusionTimeoutSec: number
}

export interface MemorySettings {
  updateRate: number
  maxIdentities: number
  qualityGate: number
}

export interface VisualizationSettings {
  showBoundingBoxes: boolean
  showTrackIds: boolean
  showTrajectories: boolean
  showConfidence: boolean
  showOcclusion: boolean
  showIdentityHistory: boolean
  showReIdentificationEvents: boolean
}

export interface Settings {
  detector: DetectorSettings
  tracker: TrackerSettings
  reid: ReIdSettings
  memory: MemorySettings
  cameraMotionMode: CameraMotionMode
  visualization: VisualizationSettings
}

export interface UpdateSettingsRequest {
  settings: Partial<Settings>
}