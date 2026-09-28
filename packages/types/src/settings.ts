export type PipelineCameraMotionMode = 'static' | 'drift'

export interface PipelineSettingsValues {
  confidenceThreshold: number
  reidThreshold: number
  memoryUpdateRate: number
  occlusionTimeoutSec: number
  cameraMotionMode: PipelineCameraMotionMode
  trackerMatchThreshold: number
  trackerBufferFrames: number
  showTrackVisualizer: boolean
  showIdentitiesPanel: boolean
  showReidPanel: boolean
  showMotionPanel: boolean
  showAnalyticsPanel: boolean
}

export interface SettingsResponse {
  values: PipelineSettingsValues
  revision: number
  updatedAt: string | null
}

export interface UpdateSettingsPayload {
  values: Partial<PipelineSettingsValues>
}
