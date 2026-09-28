export type ExperimentStatus = 'running' | 'completed' | 'failed'

export type ExperimentTracker = 'mock' | 'bytetrack'

export interface ExperimentMetrics {
  idf1: number
  hota: number
  idSwitches: number
  trackFragmentation: number
  countMae: number
  countMape: number
  identityRecoveryRate: number
}

export interface Experiment {
  id: string
  name: string
  status: ExperimentStatus
  tracker: ExperimentTracker
  scenario: string
  numFrames: number
  config: Record<string, unknown> | null
  metrics: ExperimentMetrics | null
  error: string | null
  createdAt: string | null
  completedAt: string | null
}

export interface ExperimentListResponse {
  experiments: Experiment[]
  total: number
}

export interface CreateExperimentRequest {
  name?: string
  tracker: ExperimentTracker
  scenario?: string
  num_frames: number
}
