import type { CameraMotionMode } from './common'

export type ExperimentStatus = 'queued' | 'running' | 'completed' | 'failed'

export interface ExperimentConfig {
  datasetName: string
  detector: string
  tracker: string
  identityModel: string
  reidThreshold: number
  memoryUpdateRate: number
  maxIdentityMemory: number
  occlusionTimeoutSec: number
  cameraMotionMode: CameraMotionMode
  occlusionDurationSec: number | null
  viewpointAngle: number | null
}

export interface Experiment {
  id: string
  name: string
  description: string
  config: ExperimentConfig
  status: ExperimentStatus
  metrics: EvaluationMetrics | null
  createdAt: string
  startedAt: string | null
  completedAt: string | null
  error: string | null
}

export interface EvaluationMetricValue {
  name: string
  value: number
  description: string
  category: 'identification' | 'framewise' | 'counting'
}

export interface EvaluationMetrics {
  idf1: number
  hota: number
  identityRecoveryRate: number
  idSwitches: number
  trackFragmentation: number
  mape: number
  mae: number
  mota?: number
  perTrackerMetrics: Record<string, Record<string, number>>
}

export interface BaselineComparison {
  tracker: string
  idf1: number
  hota: number
  idSwitches: number
  mapPe: number
  mae: number
}

export interface EvaluationResult {
  id: string
  experimentName: string
  videoId: string | null
  tracker: string
  detector: string
  identityModel: string
  metrics: EvaluationMetrics
  baselineComparisons: BaselineComparison[]
  createdAt: string
}

export interface ExperimentListResponse {
  experiments: Experiment[]
  total: number
}

export interface CreateExperimentRequest {
  name: string
  description?: string
  config: ExperimentConfig
}

export interface CreateExperimentResponse {
  experiment: Experiment
}