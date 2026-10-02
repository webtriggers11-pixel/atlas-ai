/** App shell: navbar + routed pages + global toaster. */
import { lazy, Suspense } from 'react'
import { Link, Route, Routes } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { Button, Skeleton } from '@/components/kit'
import { Navbar } from '@/components/layout'
import ProjectsPage from '@/pages/ProjectsPage'
import ProjectPage from '@/pages/ProjectPage'

// The v1 explorer pulls in React Flow + dagre — load it only when visited
const ExplorePage = lazy(() => import('@/pages/ExplorePage'))

/** 404 page. */
function NotFound() {
  return (
    <div className="mx-auto flex min-h-[70vh] max-w-6xl flex-col items-start justify-center gap-4 px-6">
      <p className="font-mono text-sm text-muted">404</p>
      <h1 className="text-4xl font-semibold tracking-tighter">This page doesn&apos;t exist.</h1>
      <Link to="/"><Button>Back to projects</Button></Link>
    </div>
  )
}

export default function App() {
  return (
    <div className="flex min-h-screen flex-col">
      <Navbar />
      <main className="flex-1">
        <Suspense fallback={<div className="mx-auto max-w-6xl px-6 pt-36"><Skeleton className="h-96" /></div>}>
          <Routes>
            <Route path="/" element={<ProjectsPage />} />
            <Route path="/projects/:projectId" element={<ProjectPage />} />
            <Route path="/explore" element={<ExplorePage />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </Suspense>
      </main>
      <Toaster
        position="bottom-right"
        toastOptions={{
          style: {
            background: 'var(--surface)', color: 'var(--foreground)', border: '1px solid var(--border)',
            borderRadius: 0, fontSize: '14px', fontFamily: 'var(--font-sans)',
          },
        }}
      />
    </div>
  )
}
