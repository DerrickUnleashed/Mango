import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, fireEvent, cleanup } from '@testing-library/react'
import { ThemeProvider } from './ThemeProvider'
import { ThemeToggle } from './ThemeToggle'

describe('ThemeToggle', () => {
  beforeEach(() => {
    cleanup()
    window.localStorage.clear()
    document.documentElement.removeAttribute('data-theme')
  })

  it('renders a dark-first toggle with the correct label', () => {
    render(
      <ThemeProvider>
        <ThemeToggle />
      </ThemeProvider>,
    )
    const toggle = screen.getByRole('button', { name: 'Switch to light theme' })
    expect(toggle).toBeInTheDocument()
    expect(toggle).not.toHaveClass('is-light')
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark')
  })

  it('switches to light on click and persists the choice', () => {
    render(
      <ThemeProvider>
        <ThemeToggle />
      </ThemeProvider>,
    )
    fireEvent.click(screen.getByRole('button'))
    expect(document.documentElement.getAttribute('data-theme')).toBe('light')
    expect(screen.getByRole('button', { name: 'Switch to dark theme' })).toBeInTheDocument()
    expect(window.localStorage.getItem('orchardvision-theme')).toBe('light')
  })

  it('restores a stored light theme on mount', () => {
    window.localStorage.setItem('orchardvision-theme', 'light')
    render(
      <ThemeProvider>
        <ThemeToggle />
      </ThemeProvider>,
    )
    expect(document.documentElement.getAttribute('data-theme')).toBe('light')
    expect(screen.getByRole('button', { name: 'Switch to dark theme' })).toBeInTheDocument()
  })

  it('uses the system preference when nothing is stored', () => {
    const spy = vi.spyOn(window, 'matchMedia')
    spy.mockReturnValue({ matches: true } as MediaQueryList)
    render(
      <ThemeProvider>
        <ThemeToggle />
      </ThemeProvider>,
    )
    expect(document.documentElement.getAttribute('data-theme')).toBe('light')
    spy.mockRestore()
  })
})
