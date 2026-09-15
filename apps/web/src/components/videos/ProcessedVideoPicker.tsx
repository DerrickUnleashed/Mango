import type { Video } from '@orchardvision/types'

interface ProcessedVideoPickerProps {
  processed: Video[]
  value: string | null
  onChange: (videoId: string) => void
}

export function ProcessedVideoPicker({ processed, value, onChange }: ProcessedVideoPickerProps) {
  if (processed.length === 0) return null
  return (
    <label className="flex flex-col gap-1 text-sm">
      <span className="text-surface-400">Processed video</span>
      <select
        aria-label="Select processed video"
        value={value ?? processed[0]!.id}
        onChange={(e) => onChange(e.target.value)}
        className="glass-soft cursor-pointer rounded-lg px-3 py-2 text-surface-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-orchard-400"
      >
        {processed.map((video) => (
          <option key={video.id} value={video.id}>
            {video.originalName}
          </option>
        ))}
      </select>
    </label>
  )
}
