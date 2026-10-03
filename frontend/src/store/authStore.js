/**
 * Sign-in state (Phase 12). Login is optional: only servers with AUTH_ENABLED=true ask for it.
 * The token is kept in localStorage so a refresh keeps you signed in; any 401 clears it.
 */
import { create } from 'zustand'

const TOKEN_KEY = 'atlas-token'
const EMAIL_KEY = 'atlas-email'

/** Read a localStorage key, tolerating blocked storage. */
function read(key) {
  try { return localStorage.getItem(key) } catch { return null }
}

/** Write (or remove when value is null) a localStorage key, tolerating blocked storage. */
function write(key, value) {
  try {
    if (value == null) localStorage.removeItem(key)
    else localStorage.setItem(key, value)
  } catch { /* storage blocked: session lasts until refresh */ }
}

export const useAuth = create((set) => ({
  token: read(TOKEN_KEY),
  email: read(EMAIL_KEY),

  /** Remember a fresh session from /auth/login or /auth/register. */
  signIn: ({ token, email }) => {
    write(TOKEN_KEY, token)
    write(EMAIL_KEY, email)
    set({ token, email })
  },

  /** Forget the session (sign-out button, or the server answered 401). */
  signOut: () => {
    write(TOKEN_KEY, null)
    write(EMAIL_KEY, null)
    set({ token: null, email: null })
  },
}))

/** Current token for request headers (outside React). */
export const currentToken = () => useAuth.getState().token
