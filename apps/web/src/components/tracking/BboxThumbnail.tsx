import { useEffect, useRef } from 'react'
import { videoFrameUrl } from '../../api/videos'

const FRAME_WIDTH = 320

interface BboxThumbnailProps {
  videoId: string
  frameId: number
  bbox: [number, number, number, number] | null
  videoWidth: number | null
  videoHeight: number | null
  size?: number
}

export function BboxThumbnail({
  videoId,
  frameId,
  bbox,
  videoWidth,
  videoHeight,
  size = 112,
}: BboxThumbnailProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || !bbox || !videoWidth || !videoHeight) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const [x, y, w, h] = bbox
    if (w <= 0 || h <= 0) return

    const nx = x / videoWidth
    const ny = y / videoHeight
    const nw = w / videoWidth
    const nh = h / videoHeight

    const image = new Image()
    image.src = videoFrameUrl(videoId, frameId, FRAME_WIDTH)
    image.onload = () => {
      const sourceX = Math.min(1, Math.max(0, nx)) * image.naturalWidth
      const sourceY = Math.min(1, Math.max(0, ny)) * image.naturalHeight
      const sourceW = Math.min(1 - sourceX / image.naturalWidth, nw) * image.naturalWidth
      const sourceH = Math.min(1 - sourceY / image.naturalHeight, nh) * image.naturalHeight
      if (sourceW <= 0 || sourceH <= 0) return
      ctx.clearRect(0, 0, size, size)
      ctx.drawImage(image, sourceX, sourceY, sourceW, sourceH, 0, 0, size, size)
    }
    return () => {
      image.onload = null
    }
  }, [videoId, frameId, bbox, videoWidth, videoHeight, size])

  if (!bbox || !videoWidth || !videoHeight) {
    return (
      <span
        className="block h-28 w-28 rounded-md border border-surface-700 bg-surface-800 text-xs text-surface-500"
        aria-label={`Crop of frame ${frameId}`}
        role="img"
      >
        <span className="flex h-full items-center justify-center">no bbox</span>
      </span>
    )
  }

  return (
    <canvas
      ref={canvasRef}
      width={size}
      height={size}
      role="img"
      aria-label={`Crop of frame ${frameId}`}
      className="h-28 w-28 rounded-md border border-surface-700"
    />
  )
}
