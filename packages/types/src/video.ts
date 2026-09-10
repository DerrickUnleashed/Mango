import type { JobStatus, ProcessingStage } from './common'

export interface Video {
  id: string
  filename: string
  originalName: string
  mimeType: string
  sizeBytes: number
  width: number | null
  height: number | null
  frameCount: number | null
  fps: number | null
  durationSeconds: number | null
  codec: string | null
  status: 'uploaded' | 'processing' | 'processed' | 'failed'
  createdAt: string
  processingJob: ProcessingJob | null
}

export interface ProcessingJob {
  id: string
  videoId: string
  status: JobStatus
  stage: ProcessingStage
  progress: number
  error: string | null
  message: string | null
  config: PipelineConfig | null
  inferenceMode: InferenceModeOrigin
  startedAt: string | null
  completedAt: string | null
  createdAt: string
}

export interface PipelineConfig {
  inference_mode: 'mock' | 'real'
  confidence_threshold: number
  tracker: 'mock' | 'bytetrack'
  camera_motion: 'static' | 'drift'
  reid_threshold: number
  memory_update_rate: number
  max_frames: number | null
}

export type InferenceModeOrigin = 'mock' | 'real'

export interface UploadVideoResponse {
  video: Video
}

export interface VideoListResponse {
  videos: Video[]
  total: number
}

export interface ProcessVideoRequest {
  confidenceThreshold?: number
  inferenceMode?: 'mock' | 'real'
  tracker?: 'mock' | 'bytetrack'
  cameraMotion?: 'static' | 'drift'
  maxFrames?: number
}

export interface ProcessVideoResponse {
  job: ProcessingJob
}