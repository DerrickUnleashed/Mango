import { NavLink, Outlet, useLocation } from 'react-router-dom'
import type { ReactNode } from 'react'

const navItems = [
  { to: '/', label: 'Dashboard', icon: 'grid', end: true },
  { to: '/videos', label: 'Videos', icon: 'film' },
  { to: '/identities', label: 'Identities', icon: 'user' },
  { to: '/reidentification', label: 'Re-ID', icon: 'refresh' },
  { to: '/analytics', label: 'Analytics', icon: 'chart', match: '/videos/' },
  { to: '/evaluation', label: 'Evaluation', icon: 'target' },
  { to: '/experiments', label: 'Experiments', icon: 'flask' },
  { to: '/settings', label: 'Settings', icon: 'gear' },
]

function Icon({ name }: { name: string }) {
  const paths: Record<string, string> = {
    grid: 'M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z',
    film: 'M7 3h10a4 4 0 0 1 4 4v10a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4V7a4 4 0 0 1 4-4zM3 8h18M3 16h18M8 8v13M16 8v13',
    user: 'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM4 21a8 8 0 0 1 16 0H4z',
    refresh: 'M4 12a8 8 0 1 1 2.34 5.66M4 12v-6M4 12h6',
    chart: 'M4 20h16M6 16v-5M10 16V8M14 16v-7M18 16v-4',
    target: 'M12 12a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20z',
    flask:
      'M9 3h6M10 3v6l-5.5 8a2.5 2.5 0 0 0 2.1 3.8h10.8a2.5 2.5 0 0 0 2.1-3.8L14 9V3M7.2 14h9.6',
    gear: 'M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z',
  }
  return (
    <svg
      className="h-5 w-5"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={paths[name]} />
    </svg>
  )
}

function SidebarLink({
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
        `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
          isActive
            ? 'bg-orchard-800/60 text-orchard-200'
            : 'text-surface-400 hover:bg-surface-800 hover:text-surface-100'
        }`
      }
    >
      <Icon name={icon} />
      {label}
    </NavLink>
  )
}

function Breadcrumbs() {
  const { pathname } = useLocation()
  const segments = pathname.split('/').filter(Boolean)
  if (segments.length === 0) return null
  return (
    <nav className="hidden text-sm text-surface-500 md:flex" aria-label="Breadcrumb">
      {segments.map((seg, i) => (
        <span key={`${seg}-${i}`} className="flex items-center gap-2">
          {i > 0 && <span aria-hidden="true">/</span>}
          <span>{decodeURIComponent(seg)}</span>
        </span>
      ))}
    </nav>
  )
}

function Sidebar({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen bg-surface-950">
      <aside className="hidden w-60 shrink-0 flex-col border-r border-surface-800 bg-surface-900/60 md:flex">
        <div className="flex items-center gap-2 px-4 py-5">
          <div
            className="flex h-8 w-8 items-center justify-center rounded-lg bg-orchard-600 text-white"
            aria-hidden="true"
          >
            <svg
              className="h-5 w-5"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
            >
              <path
                d="M4 20V10M4 8V4M10 20v-6M10 12V4M16 20V14M16 12V4M22 20v-4M22 14V4"
                strokeLinecap="round"
              />
            </svg>
          </div>
          <div>
            <p className="text-sm font-semibold text-surface-50">OrchardVision</p>
            <p className="text-xs text-surface-500">Fruit Tracking Research</p>
          </div>
        </div>
        <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-2" aria-label="Primary">
          {navItems.map((item) => (
            <SidebarLink key={item.to} {...item} />
          ))}
        </nav>
        <div className="border-t border-surface-800 px-4 py-4">
          <p className="text-xs text-surface-500">Inference: Mock / Demo</p>
          <p className="text-xs text-surface-600">v0.1.0</p>
        </div>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 shrink-0 items-center justify-between border-b border-surface-800 bg-surface-900/40 px-4">
          <Breadcrumbs />
          <div className="flex items-center gap-3">
            <span className="rounded-full border border-orchard-800 bg-orchard-900 px-2.5 py-1 text-xs font-medium text-orchard-300">
              Mock Mode
            </span>
          </div>
        </header>
        <main className="min-h-0 flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </div>
  )
}

export function AppLayout() {
  return (
    <Sidebar>
      <Outlet />
    </Sidebar>
  )
}
