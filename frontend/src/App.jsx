/** Routes inside the app shell (sidebar + topbar) + global toaster. */
import { lazy, Suspense } from 'react'
import { Link, Navigate, Route, Routes, useParams } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { Button, Skeleton } from '@/components/kit'
import { AppShell, PageBody } from '@/components/layout'
import DashboardPage from '@/pages/DashboardPage'
import AnalysesPage from '@/pages/AnalysesPage'
import NewAnalysisPage from '@/pages/NewAnalysisPage'
import AnalysisPage from '@/pages/AnalysisPage'
import DocumentsPage from '@/pages/DocumentsPage'
import SettingsPage from '@/pages/SettingsPage'

// The v1 topic explorer pulls in its own graph code — load it only when visited
const ExplorePage = lazy(() => import('@/pages/ExplorePage'))

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
      <Link to="/"><Button>Back to dashboard</Button></Link>
    </PageBody>
  )
}

export default function App() {
  return (
    <AppShell>
      <Suspense fallback={<PageBody><Skeleton className="h-96" /></PageBody>}>
        <Routes>
          <Route path="/" element={<DashboardPage />} />
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
