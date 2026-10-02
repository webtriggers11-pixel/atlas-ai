/**
 * V2 API client — every call to /api/v1 goes through here.
 * (The v1 topic explorer keeps its own client in src/api.js.)
 */
export const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export class ApiError extends Error {
  /** Error carrying the HTTP status and the backend's `detail` message. */
  constructor(status, message) {
    super(message)
    this.status = status
  }
}

/** fetch wrapper: JSON in/out, FastAPI `detail` surfaced as the error message, 204 → null. */
async function request(method, path, { json, form } = {}) {
  let res
  try {
    res = await fetch(`${API_BASE}/api/v1${path}`, {
      method,
      headers: json ? { 'Content-Type': 'application/json' } : undefined,
      body: json ? JSON.stringify(json) : form,
    })
  } catch {
    throw new ApiError(0, `Can't reach the backend at ${API_BASE}. Is it running?`)
  }
  if (res.status === 204) return null
  const body = await res.json().catch(() => null)
  if (!res.ok) {
    const detail = body?.detail
    const message = Array.isArray(detail)
      ? detail.map((d) => `${d.loc?.slice(1).join('.') || 'field'}: ${d.msg}`).join('; ')
      : detail || `Request failed (${res.status})`
    throw new ApiError(res.status, message)
  }
  return body
}

export const api = {
  // Projects
  listProjects: () => request('GET', '/projects'),
  getProject: (id) => request('GET', `/projects/${id}`),
  createProject: (name, preset) => request('POST', '/projects', { json: { name, preset } }),
  renameProject: (id, name) => request('PATCH', `/projects/${id}`, { json: { name } }),
  deleteProject: (id) => request('DELETE', `/projects/${id}`),

  // Documents
  listDocuments: (projectId) => request('GET', `/projects/${projectId}/documents`),
  uploadFile: (projectId, role, file) => {
    const form = new FormData()
    form.append('role', role)
    form.append('file', file)
    return request('POST', `/projects/${projectId}/documents`, { form })
  },
  uploadText: (projectId, role, title, text) => {
    const form = new FormData()
    form.append('role', role)
    form.append('title', title)
    form.append('text', text)
    return request('POST', `/projects/${projectId}/documents`, { form })
  },
  listChunks: (documentId) => request('GET', `/documents/${documentId}/chunks`),
  reprocessDocument: (documentId) => request('POST', `/documents/${documentId}/reprocess`),
  deleteDocument: (documentId) => request('DELETE', `/documents/${documentId}`),

  // Requirements
  listRequirements: (projectId) => request('GET', `/projects/${projectId}/requirements`),
  extractRequirements: (projectId) => request('POST', `/projects/${projectId}/requirements/extract`),
  addRequirement: (projectId, text, section) =>
    request('POST', `/projects/${projectId}/requirements`, { json: { text, section: section || null } }),
  updateRequirement: (id, patch) => request('PATCH', `/requirements/${id}`, { json: patch }),
  approveAll: (projectId) => request('POST', `/projects/${projectId}/requirements/approve-all`),
  mergeRequirements: (projectId, ids, text) =>
    request('POST', `/projects/${projectId}/requirements/merge`, { json: { ids, text: text || null } }),

  // Analysis
  analyze: (projectId) => request('POST', `/projects/${projectId}/analyze`),
  listRuns: (projectId) => request('GET', `/projects/${projectId}/runs`),
  getRun: (runId) => request('GET', `/runs/${runId}`),
  listFindings: (runId) => request('GET', `/runs/${runId}/findings`),

  // Global
  listAllDocuments: (search) => request('GET', `/documents${search ? `?search=${encodeURIComponent(search)}` : ''}`),
  getSettings: () => request('GET', '/settings'),

  // Retrieval debugging
  search: (projectId, query, role, mode) =>
    request('POST', `/projects/${projectId}/search`, { json: { query, role: role || null, k: 8, mode: mode || null } }),
}
