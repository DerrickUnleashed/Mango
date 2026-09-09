import type {
  AnalyticsSummary,
  CameraMotionEstimate,
  PersistedDetectionListResponse,
  PersistedIdentityListResponse,
  PersistedReidListResponse,
  PersistedTrackListResponse,
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

export function getTracks(id: string): Promise<PersistedTrackListResponse> {
  return apiRequest<PersistedTrackListResponse>(`/videos/${id}/tracks`)
}

export function getIdentities(id: string): Promise<PersistedIdentityListResponse> {
  return apiRequest<PersistedIdentityListResponse>(`/videos/${id}/identities`)
}

export function getReidEvents(id: string): Promise<PersistedReidListResponse> {
  return apiRequest<PersistedReidListResponse>(`/videos/${id}/reid-events`)
}

export function getDetections(
  id: string,
  frameId?: number,
): Promise<PersistedDetectionListResponse> {
  const query = frameId === undefined ? '' : `?frame_id=${frameId}`
  return apiRequest<PersistedDetectionListResponse>(`/videos/${id}/detections${query}`)
}

export function getMotionEstimate(id: string): Promise<CameraMotionEstimate | null> {
  return apiRequest<{ estimate: CameraMotionEstimate | null }>(
    `/videos/${id}/motion`,
  ).then((body) => body.estimate)
}

export function getAnalytics(
  id: string,
): Promise<AnalyticsSummary | null> {
  return apiRequest<{ summary: AnalyticsSummary | null }>(
    `/videos/${id}/analytics`,
  ).then((body) => body.summary)
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