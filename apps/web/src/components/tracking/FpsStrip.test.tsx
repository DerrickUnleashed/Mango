import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import type { FrameTiming } from '@orchardvision/types'
import { FpsStrip } from './FpsStrip'

const timings: FrameTiming[] = [
  { id: 't1', videoId: 'v', frameId: 0, elapsedMs: 4, fps: 250 },
  { id: 't2', videoId: 'v', frameId: 1, elapsedMs: 10, fps: 100 },
  { id: 't3', videoId: 'v', frameId: 2, elapsedMs: 8, fps: 125 },
]

describe('FpsStrip', () => {
  it('renders a bar per frame with an average', () => {
    render(<FpsStrip timings={timings} />)
    expect(screen.getByRole('img', { name: /strip chart/i })).toBeInTheDocument()
    expect(screen.getByText(/3 frames · avg 158 fps/)).toBeInTheDocument()
  })

  it('shows an empty message without data', () => {
    render(<FpsStrip timings={[]} />)
    expect(screen.getByText(/No per-frame timing data/)).toBeInTheDocument()
  })

  it('tolerates zero values', () => {
    render(
      <FpsStrip
        timings={[
          { id: 't', videoId: 'v', frameId: 0, elapsedMs: 0, fps: 0 },
          { id: 't2', videoId: 'v', frameId: 1, elapsedMs: 5, fps: 200 },
        ]}
      />,
    )
    expect(screen.getByRole('img')).toBeInTheDocument()
  })
})
