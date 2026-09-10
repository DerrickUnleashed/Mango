import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { AnalyticsPage } from './AnalyticsPage'
import { EvaluationPage } from './EvaluationPage'
import { IdentitiesPage } from './IdentitiesPage'
import { ReidentificationPage } from './ReidentificationPage'

describe('placeholder pages', () => {
  it('AnalyticsPage shows the analytics empty state', () => {
    render(<AnalyticsPage />)
    expect(screen.getByText('Analytics will appear here')).toBeInTheDocument()
  })

  it('EvaluationPage shows the evaluation empty state', () => {
    render(<EvaluationPage />)
    expect(screen.getByText('No evaluations yet')).toBeInTheDocument()
  })

  it('IdentitiesPage shows the identity explorer empty state', () => {
    render(<IdentitiesPage />)
    expect(screen.getByText('Identity Explorer')).toBeInTheDocument()
    expect(screen.getByText('No identities tracked yet')).toBeInTheDocument()
  })

  it('ReidentificationPage shows the re-id empty state', () => {
    render(<ReidentificationPage />)
    expect(screen.getByText('No re-identification events')).toBeInTheDocument()
  })
})
