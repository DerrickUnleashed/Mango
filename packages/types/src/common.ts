export interface BoundingBox {
  x: number
  y: number
  width: number
  height: number
}

export type VisibilityState = 'visible' | 'partial' | 'occluded' | 'lost' | 'reidentified'

export type JobStatus = 'queued' | 'running' | 'completed' | 'failed' | 'cancelled'

export type InferenceMode = 'mock' | 'real'

export type ProcessingStage =
  | 'uploaded'
  | 'extracting_frames'
  | 'detecting'
  | 'tracking'
  | 'embedding'
  | 'memory'
  | 'reid'
  | 'analytics'
  | 'completed'
  | 'failed'

export type CameraMotionMode = 'static' | 'slow' | 'fast' | 'handheld'