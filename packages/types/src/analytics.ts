export interface CameraMotionEstimate {
  id: string
  videoId: string
  source: string
  dxPerFrame: number
  dyPerFrame: number
  meanAbsShift: number
  framesAnalyzed: number
  confidence: number
  compensationApplied: boolean
}

export interface MultiMotionResponse {
  estimate: CameraMotionEstimate | null
  compensationApplied: boolean | null
}

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
