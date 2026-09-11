import { useTheme } from './ThemeProvider'

function Sun() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
    >
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
    </svg>
  )
}

function Moon() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" />
    </svg>
  )
}

export function ThemeToggle() {
  const { theme, toggleTheme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <button
      type="button"
      data-theme-toggle
      onClick={toggleTheme}
      aria-label={isDark ? 'Switch to light theme' : 'Switch to dark theme'}
      className={`${isDark ? '' : 'is-light '}theme-toggle`}
    >
      <span className="theme-toggle-track">
        <span className="theme-toggle-icon theme-toggle-icon-sun">
          <Sun />
        </span>
        <span className="theme-toggle-icon theme-toggle-icon-moon">
          <Moon />
        </span>
        <span className="theme-toggle-thumb">{isDark ? <Moon /> : <Sun />}</span>
      </span>
    </button>
  )
}
