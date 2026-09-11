import { useMemo, useState } from 'react'
import type { Video } from '@orchardvision/types'
import { useVideos } from './useVideos'

export function useProcessedVideoSelection(): {
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
  const selected = selection ?? processed[0]?.id ?? null
  return { processed, selected, isLoading: videos.isLoading, setSelected: setSelection }
}
