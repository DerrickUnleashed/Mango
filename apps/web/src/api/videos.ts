import type {
  ProcessVideoRequest,
  ProcessVideoResponse,
  UploadVideoResponse,
  Video,
  VideoListResponse,
} from '@orchardvision/types'
import { apiRequest, apiUpload } from './client'

export function getVideos(): Promise<VideoListResponse> {
  return apiRequest<VideoListResponse>('/videos')
}

export function getVideo(id: string): Promise<Video> {
  return apiRequest<Video>(`/videos/${id}`)
}

export function uploadVideo(
  file: File,
  onProgress?: (percent: number) => void,
): Promise<UploadVideoResponse> {
  const formData = new FormData()
  formData.append('file', file)
  return apiUpload<UploadVideoResponse>('/videos', formData, onProgress)
}

export function deleteVideo(id: string): Promise<{ ok: boolean }> {
  return apiRequest<{ ok: boolean }>(`/videos/${id}`, { method: 'DELETE' })
}

export function processVideo(
  id: string,
  request: ProcessVideoRequest,
): Promise<ProcessVideoResponse> {
  return apiRequest<ProcessVideoResponse>(`/videos/${id}/process`, {
    method: 'POST',
    body: JSON.stringify(request),
  })
}

export function getJob(jobId: string): Promise<{ job: unknown }> {
  return apiRequest<{ job: unknown }>(`/jobs/${jobId}`)
}

export function getHealth(): Promise<{
  status: string
  service: string
  version: string
}> {
  return apiRequest<{ status: string; service: string; version: string }>(
    '/health',
  )
}

export * from './client'