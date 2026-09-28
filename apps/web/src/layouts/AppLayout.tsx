import { Link, NavLink, Outlet } from 'react-router-dom'
import { ThemeToggle } from '../components/ui/ThemeToggle'
import { LogoMark } from '../components/ui/Logo'

const navItems = [
  { to: '/dashboard', label: 'Dashboard', icon: 'grid', end: true },
  { to: '/videos', label: 'Videos', icon: 'film' },
  { to: '/identities', label: 'Identities', icon: 'user' },
  { to: '/reidentification', label: 'Re-ID', icon: 'refresh' },
  { to: '/evaluation', label: 'Evaluation', icon: 'target' },
  { to: '/experiments', label: 'Experiments', icon: 'flask' },
  { to: '/settings', label: 'Settings', icon: 'gear' },
]

function Icon({ name, className = 'h-4 w-4' }: { name: string; className?: string }) {
  const paths: Record<string, string> = {
    grid: 'M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z',
    film: 'M7 3h10a4 4 0 0 1 4 4v10a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4V7a4 4 0 0 1 4-4zM3 8h18M3 16h18M8 8v13M16 8v13',
    user: 'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM4 21a8 8 0 0 1 16 0H4z',
    refresh: 'M4 12a8 8 0 1 1 2.34 5.66M4 12v-6M4 12h6',
    target: 'M12 12a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20z',
    flask:
      'M9 3h6M10 3v6l-5.5 8a2.5 2.5 0 0 0 2.1 3.8h10.8a2.5 2.5 0 0 0 2.1-3.8L14 9V3M7.2 14h9.6',
    gear: 'M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z',
  }
  const d = paths[name]
  if (!d) return null
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={d} />
    </svg>
  )
}

function HeaderTab({
  to,
  label,
  icon,
  end,
}: {
  to: string
  label: string
  icon: string
  end?: boolean
}) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        `clay-press flex shrink-0 items-center gap-2 rounded-full px-3.5 py-1.5 text-sm font-medium ${
          isActive
            ? 'bg-mango text-surface-950 clay-press-glow'
            : 'text-surface-400 hover:text-surface-50'
        }`
      }
    >
      <Icon name={icon} />
      {label}
    </NavLink>
  )
}

function Header() {
  return (
    <header className="sticky top-0 z-30 px-4 pt-3">
      <nav
        className="clay mx-auto flex max-w-[100rem] items-center gap-3 rounded-2xl px-3 py-2.5"
        aria-label="Primary"
      >
        <Link
          to="/"
          className="flex shrink-0 cursor-pointer items-center gap-2 rounded-xl px-1.5 py-1 transition-colors hover:text-surface-50"
          title="Back to the landing page"
        >
          <LogoMark className="h-8 w-8" />
          <span className="font-display hidden text-sm font-semibold text-surface-50 sm:block">
            OrchardVision
          </span>
        </Link>
        <div
          className="no-scrollbar flex min-w-0 flex-1 items-center gap-1 overflow-x-auto"
          aria-label="Pages"
        >
          {navItems.map((item) => (
            <HeaderTab key={item.to} {...item} />
          ))}
        </div>
        <div className="flex shrink-0 items-center gap-3">
          <span
            className="clay-chip rounded-full px-2.5 py-1 text-xs font-medium text-emerald-300"
            title="Inference status"
          >
            <span className="mr-1.5 inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" />
            Live
          </span>
          <ThemeToggle />
        </div>
      </nav>
    </header>
  )
}

export function AppLayout() {
  return (
    <div className="relative min-h-screen">
      <div
        className="blob blob-orange blob-slow"
        style={{ width: '34rem', height: '34rem', left: '-14rem', bottom: '-14rem', opacity: 0.14 }}
      />
      <div
        className="blob blob-sky blob-fast"
        style={{ width: '26rem', height: '26rem', right: '-12rem', top: '6rem', opacity: 0.12 }}
      />
      <Header />
      <main className="relative min-h-0 flex-1 p-6">
        <Outlet />
      </main>
    </div>
  )
}
