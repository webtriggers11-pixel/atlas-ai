/** Thin fetch wrapper — all API calls go through here, nowhere else. */
import { currentToken, useAuth } from '@/store/authStore'

const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

async function request(method, path, body) {
  const token = currentToken()
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: {
      ...(body ? { 'Content-Type': 'application/json' } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  })
  if (res.status === 401) useAuth.getState().signOut()
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `Request failed: ${res.status}`)
  }
  if (res.status === 204) return null
  return res.json()
}

export const createMap   = (topic, depth)            => request('POST',   '/maps',                                    { topic, depth })
export const listMaps    = ()                         => request('GET',    '/maps')
export const getMap      = (id)                       => request('GET',    `/maps/${id}`)
export const expandNode  = (mapId, nodeId, depth)     => request('POST',   `/maps/${mapId}/nodes/${nodeId}/expand`,    { depth })
export const changeDepth = (mapId, nodeId, depth)     => request('PATCH',  `/maps/${mapId}/nodes/${nodeId}/depth`,    { depth })
export const deleteMap   = (id)                       => request('DELETE', `/maps/${id}`)
