import { useMemo, useState } from 'react'
import type { Video } from '@orchardvision/types'
import { useVideos } from './useVideos'

export function useProcessedVideoSelection(initialVideoId?: string | null): {
  processed: Video[]
  selected: string | null
  isLoading: boolean
  setSelected: (videoId: string | null) => void
} {
  const videos = useVideos()
  const processed = useMemo(
    () => (videos.data?.videos ?? []).filter((video) => video.status === 'processed'),
    [videos.data],
  )
  const [selection, setSelection] = useState<string | null>(null)
  const fallback =
    initialVideoId && processed.some((video) => video.id === initialVideoId)
      ? initialVideoId
      : (processed[0]?.id ?? null)
  const selected = selection ?? fallback
  return { processed, selected, isLoading: videos.isLoading, setSelected: setSelection }
}
