import type { CameraMotionMode } from './common'

export interface AnalyticsSummary {
  videoId: string
  totalFrames: number
  fruitPerFrame: CountSeries[]
  uniqueIdentities: number
  totalFruitDetections: number
  totalFruitCount: number
  activeTracks: number
  lostTracks: number
  recoveredIdentities: number
  idSwitches: number
  trackFragmentation: number
  occlusionEvents: number
  avgConfidence: number
  avgTrackingFps: number
  processingSeconds: number
  confidenceDistribution: DistributionBin[]
  occlusionDurationDistribution: DistributionBin[]
  tracksPerFrame: CountSeries[]
  lossesPerFrame: CountSeries[]
}

export interface CountSeries {
  frameId: number
  count: number
}

export interface DistributionBin {
  label: string
  count: number
}

export interface DistanceMetric {
  name: string
  value: number
}

export interface CameraMotionEstimate {
  frameId: number
  mode: CameraMotionMode
  translateX: number
  translateY: number
  scale: number
  rotation: number
  confidence: number
}