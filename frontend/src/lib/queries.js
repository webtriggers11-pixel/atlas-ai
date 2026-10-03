/**
 * Server state with TanStack Query: caching, refetching and polling live here,
 * so components only describe WHAT they need.
 *
 * Polling is conditional — a query refetches every ~2s only while the backend
 * reports work in progress (document processing, extraction, analysis) and stops
 * by itself when that work finishes.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { api } from '@/lib/api'

const POLL_MS = 2000

export const keys = {
  projects: ['projects'],
  project: (id) => ['project', id],
  documents: (id) => ['documents', id],
  requirements: (id) => ['requirements', id],
  runs: (id) => ['runs', id],
  findings: (runId) => ['findings', runId],
  chunks: (docId) => ['chunks', docId],
  allDocuments: (search) => ['all-documents', search || ''],
  settings: ['settings'],
  traces: (findingId) => ['traces', findingId],
  report: (runId) => ['report', runId],
  diff: (runId) => ['diff', runId],
}

export const useProjects = () => useQuery({ queryKey: keys.projects, queryFn: api.listProjects })

export const useProject = (id) =>
  useQuery({
    queryKey: keys.project(id),
    queryFn: () => api.getProject(id),
    refetchInterval: (q) => (q.state.data?.extraction_status === 'running' ? POLL_MS : false),
  })

const BUSY_DOC = new Set(['uploaded', 'processing'])

export const useDocuments = (projectId) =>
  useQuery({
    queryKey: keys.documents(projectId),
    queryFn: () => api.listDocuments(projectId),
    // keep polling while a document is still being processed (but not if the queue is down)
    refetchInterval: (q) =>
      q.state.data?.some((d) => BUSY_DOC.has(d.status) && !d.error_message) ? POLL_MS : false,
  })

export const useRequirements = (projectId) =>
  useQuery({ queryKey: keys.requirements(projectId), queryFn: () => api.listRequirements(projectId) })

export const useRuns = (projectId) =>
  useQuery({
    queryKey: keys.runs(projectId),
    queryFn: () => api.listRuns(projectId),
    refetchInterval: (q) => (q.state.data?.some((r) => r.status === 'queued' || r.status === 'running') ? POLL_MS : false),
  })

export const useFindings = (runId, enabled = true) =>
  useQuery({ queryKey: keys.findings(runId), queryFn: () => api.listFindings(runId), enabled: Boolean(runId) && enabled })

export const useAllDocuments = (search) =>
  useQuery({ queryKey: keys.allDocuments(search), queryFn: () => api.listAllDocuments(search) })

export const useAuthStatus = () =>
  useQuery({ queryKey: ['auth-status'], queryFn: api.authStatus, staleTime: Infinity, retry: 2 })

export const useSettings = () => useQuery({ queryKey: keys.settings, queryFn: api.getSettings, staleTime: 60_000 })

export const useTraces = (findingId) =>
  useQuery({
    queryKey: keys.traces(findingId),
    queryFn: () => api.listTraces(findingId),
    enabled: Boolean(findingId),
    refetchInterval: (q) => (q.state.data?.some((t) => t.status === 'queued' || t.status === 'running') ? POLL_MS : false),
  })

export const useReport = (runId) => useQuery({ queryKey: keys.report(runId), queryFn: () => api.getReport(runId), enabled: Boolean(runId) })

export const useDiff = (runId) => useQuery({ queryKey: keys.diff(runId), queryFn: () => api.getDiff(runId), enabled: Boolean(runId) })

export const useChunks = (documentId) =>
  useQuery({ queryKey: keys.chunks(documentId), queryFn: () => api.listChunks(documentId), enabled: Boolean(documentId) })

/**
 * useMutation with the app's conventions: invalidate the given query keys on success,
 * show a toast on error (and optionally on success).
 */
export function useAction(fn, { invalidate = [], success, onSuccess } = {}) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: fn,
    onSuccess: (data, vars) => {
      invalidate.forEach((key) => qc.invalidateQueries({ queryKey: key }))
      if (success) toast.success(typeof success === 'function' ? success(data, vars) : success)
      onSuccess?.(data, vars)
    },
    onError: (err) => toast.error(err.message),
  })
}
