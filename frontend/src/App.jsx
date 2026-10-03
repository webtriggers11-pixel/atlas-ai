/** Public landing page at "/", and the app (sidebar shell + routes + toaster) everywhere else. */
import { lazy, Suspense } from 'react'
import { Link, Navigate, Route, Routes, useLocation, useParams } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { Button, ErrorState, Skeleton } from '@/components/kit'
import { useAuthStatus } from '@/lib/queries'
import { useAuth } from '@/store/authStore'
import LoginPage from '@/pages/LoginPage'
import { AppShell, PageBody } from '@/components/layout'
import DashboardPage from '@/pages/DashboardPage'
import AnalysesPage from '@/pages/AnalysesPage'
import NewAnalysisPage from '@/pages/NewAnalysisPage'
import AnalysisPage from '@/pages/AnalysisPage'
import DocumentsPage from '@/pages/DocumentsPage'
import SettingsPage from '@/pages/SettingsPage'

// The v1 topic explorer pulls in its own graph code — load it only when visited
const ExplorePage = lazy(() => import('@/pages/ExplorePage'))
// The landing page is only for first-time visitors — keep it out of the app bundle
const LandingPage = lazy(() => import('@/pages/LandingPage'))

/** Old /projects/:id links → /analyses/:id. */
function LegacyProjectRedirect() {
  const { projectId } = useParams()
  return <Navigate to={`/analyses/${projectId}`} replace />
}

/** 404 page. */
function NotFound() {
  return (
    <PageBody className="flex min-h-[60vh] flex-col items-start justify-center gap-3">
      <p className="font-mono text-sm text-muted">404</p>
      <h1 className="text-3xl font-semibold tracking-tight">This page doesn&apos;t exist.</h1>
      <Link to="/app"><Button>Back to dashboard</Button></Link>
    </PageBody>
  )
}

/** "/" is the public landing page; every other path is the app. */
export default function App() {
  const { pathname } = useLocation()
  if (pathname === '/') {
    return <Suspense fallback={<div className="min-h-screen bg-background" />}><LandingPage /></Suspense>
  }
  return <AuthGate />
}

/** Show the sign-in page first when the server requires login (AUTH_ENABLED=true); otherwise go straight in. */
function AuthGate() {
  const status = useAuthStatus()
  const token = useAuth((s) => s.token)
  if (status.isPending) return <div className="p-6"><Skeleton className="h-96" /></div>
  if (status.isError) return <div className="p-6"><ErrorState error={status.error} onRetry={status.refetch} /></div>
  if (status.data.enabled && !token) return <LoginPage registration={status.data.registration} />
  return <Shell />
}

/** The signed-in app: sidebar shell + routes + toaster. */
function Shell() {
  return (
    <AppShell>
      <Suspense fallback={<PageBody><Skeleton className="h-96" /></PageBody>}>
        <Routes>
          <Route path="/app" element={<DashboardPage />} />
          <Route path="/analyses" element={<AnalysesPage />} />
          <Route path="/analyses/new" element={<NewAnalysisPage />} />
          <Route path="/analyses/:analysisId" element={<AnalysisPage />} />
          <Route path="/documents" element={<DocumentsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/explore" element={<ExplorePage />} />
          <Route path="/projects/:projectId" element={<LegacyProjectRedirect />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </Suspense>
      <Toaster
        position="bottom-right"
        toastOptions={{
          style: {
            background: 'var(--surface)', color: 'var(--foreground)', border: '1px solid var(--border)',
            borderRadius: 0, fontSize: '14px', fontFamily: 'var(--font-sans)',
          },
        }}
      />
    </AppShell>
  )
}
