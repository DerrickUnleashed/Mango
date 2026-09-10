import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { StatCard } from './StatCard'

describe('StatCard', () => {
  it('renders label and value', () => {
    render(<StatCard label="Total detections" value={1234} />)
    expect(screen.getByText('Total detections')).toBeInTheDocument()
    expect(screen.getByText('1234')).toBeInTheDocument()
  })

  it('hides hint when not provided', () => {
    render(<StatCard label="Count" value={1} />)
    expect(screen.queryByText('Lower is better')).not.toBeInTheDocument()
  })

  it('shows hint when provided', () => {
    render(<StatCard label="Count" value={1} hint="Lower is better" />)
    expect(screen.getByText('Lower is better')).toBeInTheDocument()
  })
})
