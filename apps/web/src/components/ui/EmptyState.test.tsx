import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { EmptyState } from './EmptyState'

describe('EmptyState', () => {
  it('renders title and description', () => {
    render(<EmptyState title="No videos" description="Upload a video to begin." />)
    expect(screen.getByRole('status')).toBeInTheDocument()
    expect(screen.getByText('No videos')).toBeInTheDocument()
    expect(screen.getByText('Upload a video to begin.')).toBeInTheDocument()
  })
})