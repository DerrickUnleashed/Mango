import { lazy, Suspense, type ReactNode } from 'react'
import { Route, Routes } from 'react-router-dom'
import { AppLayout } from '../layouts/AppLayout'
import { DashboardPage } from '../pages/DashboardPage'
import { SettingsPage } from '../pages/SettingsPage'

const VideosPage = lazy(() =>
  import('../pages/VideosPage').then((m) => ({ default: m.VideosPage })),
)
const VideoDetailPage = lazy(() =>
  import('../pages/VideoDetailPage').then((m) => ({ default: m.VideoDetailPage })),
)
const AnalyticsPage = lazy(() =>
  import('../pages/AnalyticsPage').then((m) => ({ default: m.AnalyticsPage })),
)
const EvaluationPage = lazy(() =>
  import('../pages/EvaluationPage').then((m) => ({ default: m.EvaluationPage })),
)
const ExperimentsPage = lazy(() =>
  import('../pages/ExperimentsPage').then((m) => ({ default: m.ExperimentsPage })),
)
const IdentitiesPage = lazy(() =>
  import('../pages/IdentitiesPage').then((m) => ({ default: m.IdentitiesPage })),
)
const ReidentificationPage = lazy(() =>
  import('../pages/ReidentificationPage').then((m) => ({ default: m.ReidentificationPage })),
)

function SuspenseFallback({ children }: { children: ReactNode }) {
  return <Suspense fallback={<PageFallback />}>{children}</Suspense>
}

function PageFallback() {
  return (
    <div
      className="flex h-full items-center justify-center p-8"
      role="status"
      aria-label="Loading page"
    >
      <span className="text-surface-500">Loading…</span>
    </div>
  )
}

export function AppRouter() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<DashboardPage />} />
        <Route
          path="/videos"
          element={
            <SuspenseFallback>
              <VideosPage />
            </SuspenseFallback>
          }
        />
        <Route
          path="/videos/:videoId"
          element={
            <SuspenseFallback>
              <VideoDetailPage />
            </SuspenseFallback>
          }
        />
        <Route
          path="/videos/:videoId/analytics"
          element={
            <SuspenseFallback>
              <AnalyticsPage />
            </SuspenseFallback>
          }
        />
        <Route
          path="/identities"
          element={
            <SuspenseFallback>
              <IdentitiesPage />
            </SuspenseFallback>
          }
        />
        <Route
          path="/reidentification"
          element={
            <SuspenseFallback>
              <ReidentificationPage />
            </SuspenseFallback>
          }
        />
        <Route
          path="/evaluation"
          element={
            <SuspenseFallback>
              <EvaluationPage />
            </SuspenseFallback>
          }
        />
        <Route
          path="/experiments"
          element={
            <SuspenseFallback>
              <ExperimentsPage />
            </SuspenseFallback>
          }
        />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}

function NotFoundPage() {
  return (
    <div
      className="flex h-full flex-col items-center justify-center gap-2 p-8 text-center"
      role="alert"
    >
      <h1 className="text-2xl font-semibold">Page not found</h1>
      <p className="text-surface-400">The route you requested does not exist.</p>
    </div>
  )
}
