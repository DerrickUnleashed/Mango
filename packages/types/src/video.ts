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
  inferenceMode: InferenceModeOrigin
  startedAt: string | null
  completedAt: string | null
  createdAt: string
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
  maxFrames?: number
}

export interface ProcessVideoResponse {
  job: ProcessingJob
}