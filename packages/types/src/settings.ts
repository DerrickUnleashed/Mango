export type PipelineCameraMotionMode = 'static' | 'drift'

export interface PipelineSettingsValues {
  confidenceThreshold: number
  reidThreshold: number
  memoryUpdateRate: number
  occlusionTimeoutSec: number
  cameraMotionMode: PipelineCameraMotionMode
}

export interface SettingsResponse {
  values: PipelineSettingsValues
  revision: number
  updatedAt: string | null
}

export interface UpdateSettingsPayload {
  values: Partial<PipelineSettingsValues>
}