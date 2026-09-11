import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { ProcessVideoRequest, ProcessVideoResponse, Video } from '@orchardvision/types'
import {
  deleteVideo,
  getAnalytics,
  getDetections,
  getFrameTimings,
  getHealth,
  getIdentities,
  getIdentityObservations,
  getIdentityProjection,
  getMotionEstimate,
  getReidEvents,
  getTracks,
  getVideo,
  getVideos,
  processVideo,
  uploadVideo,
} from '../api/videos'

export function useVideos() {
  return useQuery({
    queryKey: ['videos'],
    queryFn: getVideos,
  })
}

export function useVideo(videoId: string) {
  return useQuery({
    queryKey: ['videos', videoId],
    queryFn: () => getVideo(videoId),
    enabled: Boolean(videoId),
    refetchInterval: (query) => {
      const job = query.state.data?.processingJob
      const active = job?.status === 'running' || job?.status === 'queued'
      return active ? 2000 : false
    },
  })
}

export function useTracks(videoId: string, enabled: boolean) {
  return useQuery({
    queryKey: ['videos', videoId, 'tracks'],
    queryFn: () => getTracks(videoId),
    enabled: enabled && Boolean(videoId),
  })
}

export function useIdentities(videoId: string, enabled: boolean) {
  return useQuery({
    queryKey: ['videos', videoId, 'identities'],
    queryFn: () => getIdentities(videoId),
    enabled: enabled && Boolean(videoId),
  })
}

export function useIdentityProjection(videoId: string, enabled: boolean) {
  return useQuery({
    queryKey: ['videos', videoId, 'identities', 'projection'],
    queryFn: () => getIdentityProjection(videoId),
    enabled: enabled && Boolean(videoId),
  })
}

export function useReidEvents(videoId: string, enabled: boolean) {
  return useQuery({
    queryKey: ['videos', videoId, 'reid-events'],
    queryFn: () => getReidEvents(videoId),
    enabled: enabled && Boolean(videoId),
  })
}

export function useMotionEstimate(videoId: string, enabled: boolean) {
  return useQuery({
    queryKey: ['videos', videoId, 'motion'],
    queryFn: () => getMotionEstimate(videoId),
    enabled: enabled && Boolean(videoId),
  })
}

export function useAnalytics(videoId: string, enabled: boolean) {
  return useQuery({
    queryKey: ['videos', videoId, 'analytics'],
    queryFn: () => getAnalytics(videoId),
    enabled: enabled && Boolean(videoId),
  })
}

export function useFrameTimings(videoId: string, enabled: boolean) {
  return useQuery({
    queryKey: ['videos', videoId, 'per-frame'],
    queryFn: () => getFrameTimings(videoId),
    enabled: enabled && Boolean(videoId),
  })
}

export function useIdentityObservations(
  videoId: string,
  identityId: number | null,
  enabled: boolean,
) {
  return useQuery({
    queryKey: ['videos', videoId, 'identities', identityId, 'observations'],
    queryFn: () => getIdentityObservations(videoId, identityId as number),
    enabled: enabled && identityId !== null,
  })
}

export function useFrameDetections(videoId: string, frameId: number, enabled: boolean) {
  return useQuery({
    queryKey: ['videos', videoId, 'detections', frameId],
    queryFn: () => getDetections(videoId, frameId),
    enabled: enabled && Boolean(videoId),
  })
}

export function useUploadVideo(onSuccess?: (video: Video) => void) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ file, onProgress }: { file: File; onProgress?: (p: number) => void }) =>
      uploadVideo(file, onProgress),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['videos'] })
      onSuccess?.(data.video)
    },
  })
}

export function useDeleteVideo() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (videoId: string) => deleteVideo(videoId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['videos'] })
    },
  })
}

export function useProcessVideo() {
  const queryClient = useQueryClient()
  return useMutation<
    ProcessVideoResponse,
    Error,
    { videoId: string; request: ProcessVideoRequest }
  >({
    mutationFn: ({ videoId, request }) => processVideo(videoId, request),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['videos', variables.videoId] })
      queryClient.invalidateQueries({
        queryKey: ['videos', variables.videoId, 'tracks'],
      })
      queryClient.invalidateQueries({
        queryKey: ['videos', variables.videoId, 'identities'],
      })
      queryClient.invalidateQueries({
        queryKey: ['videos', variables.videoId, 'identities', 'projection'],
      })
      queryClient.invalidateQueries({
        queryKey: ['videos', variables.videoId, 'reid-events'],
      })
      queryClient.invalidateQueries({
        queryKey: ['videos', variables.videoId, 'detections'],
      })
      queryClient.invalidateQueries({
        queryKey: ['videos', variables.videoId, 'motion'],
      })
      queryClient.invalidateQueries({
        queryKey: ['videos', variables.videoId, 'analytics'],
      })
      queryClient.invalidateQueries({
        queryKey: ['videos', variables.videoId, 'per-frame'],
      })
    },
  })
}

export function useHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: getHealth,
    refetchInterval: 30000,
    retry: 2,
  })
}
