import type {
  AnalyticsSummary,
  CameraMotionEstimate,
  CrossVideoProjectionResponse,
  FrameTimingListResponse,
  IdentityProjectionResponse,
  ObservationProjectionResponse,
  PersistedDetectionListResponse,
  PersistedIdentityListResponse,
  PersistedObservationListResponse,
  PersistedReidListResponse,
  PersistedTrackListResponse,
  ProcessVideoRequest,
  ProcessVideoResponse,
  UploadVideoResponse,
  Video,
  VideoListResponse,
} from '@orchardvision/types'
import { apiBaseUrl, apiRequest, apiUpload } from './client'

export { apiBaseUrl }

export type ProjectionMethod = 'tsne' | 'pca' | 'umap'

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

export function getIdentityProjection(
  id: string,
  method: ProjectionMethod = 'tsne',
): Promise<IdentityProjectionResponse> {
  return apiRequest<IdentityProjectionResponse>(
    `/videos/${id}/identities/projection?method=${method}`,
  )
}

export function getObservationProjection(
  id: string,
  method: ProjectionMethod = 'tsne',
): Promise<ObservationProjectionResponse> {
  return apiRequest<ObservationProjectionResponse>(
    `/videos/${id}/observations/projection?method=${method}`,
  )
}

export function getCrossVideoProjection(
  method: ProjectionMethod = 'tsne',
): Promise<CrossVideoProjectionResponse> {
  return apiRequest<CrossVideoProjectionResponse>(`/embeddings/projection?method=${method}`)
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
  return apiRequest<{ estimate: CameraMotionEstimate | null }>(`/videos/${id}/motion`).then(
    (body) => body.estimate,
  )
}

export function getAnalytics(id: string): Promise<AnalyticsSummary | null> {
  return apiRequest<{ summary: AnalyticsSummary | null }>(`/videos/${id}/analytics`).then(
    (body) => body.summary,
  )
}

export function getFrameTimings(id: string): Promise<FrameTimingListResponse> {
  return apiRequest<FrameTimingListResponse>(`/videos/${id}/per-frame`)
}

export function getIdentityObservations(
  id: string,
  identityId: number,
): Promise<PersistedObservationListResponse> {
  return apiRequest<PersistedObservationListResponse>(
    `/videos/${id}/identities/${identityId}/observations`,
  )
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

function snakeify(request: ProcessVideoRequest): Record<string, unknown> {
  const body: Record<string, unknown> = {}
  for (const [key, value] of Object.entries(request)) {
    body[key.replace(/[A-Z]/g, (char) => `_${char.toLowerCase()}`)] = value
  }
  return body
}

export function processVideo(
  id: string,
  request: ProcessVideoRequest,
): Promise<ProcessVideoResponse> {
  return apiRequest<ProcessVideoResponse>(`/videos/${id}/process`, {
    method: 'POST',
    body: JSON.stringify(snakeify(request)),
  })
}

export function getJob(jobId: string): Promise<{ job: unknown }> {
  return apiRequest<{ job: unknown }>(`/jobs/${jobId}`)
}

export function videoFileUrl(id: string): string {
  return `${apiBaseUrl}/videos/${id}/file`
}

export function videoFrameUrl(id: string, frameId: number, width?: number): string {
  const query = width === undefined ? '' : `?width=${width}`
  return `${apiBaseUrl}/videos/${id}/frames/${frameId}${query}`
}

export function getHealth(): Promise<{
  status: string
  service: string
  version: string
}> {
  return apiRequest<{ status: string; service: string; version: string }>('/health')
}

export * from './client'
