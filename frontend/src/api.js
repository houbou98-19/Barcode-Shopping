const SERVER_URL_KEY = 'serverUrl'
const SESSION_KEY = 'session'

export function getServerUrl() {
  return localStorage.getItem(SERVER_URL_KEY) || ''
}

export function setServerUrl(url) {
  if (url) {
    localStorage.setItem(SERVER_URL_KEY, url)
  } else {
    localStorage.removeItem(SERVER_URL_KEY)
  }
}

/**
 * The active profile's session, as issued by POST /api/profiles/<id>/verify-pin:
 * { token, profileId, profileName }. apiFetch() attaches its token as a
 * Bearer header on every request, since v1 write endpoints require it (#29).
 */
export function getSession() {
  const raw = localStorage.getItem(SESSION_KEY)
  return raw ? JSON.parse(raw) : null
}

export function setSession(session) {
  localStorage.setItem(SESSION_KEY, JSON.stringify(session))
}

export function clearSession() {
  localStorage.removeItem(SESSION_KEY)
}

/**
 * Builds the URL for an API path. On web/PWA, relative paths already work
 * (same origin, or the Vite dev proxy), so an unset server URL just returns
 * the path unchanged. The native Android app's WebView has no real origin
 * to resolve a relative path against, so it needs an explicit server URL
 * configured in Settings.
 */
export function apiUrl(path) {
  const base = getServerUrl()
  if (!base) return path
  return base.replace(/\/+$/, '') + path
}

/**
 * fetch() wrapper that attaches the active session's token as a Bearer
 * header (harmless on the read-only/unauthenticated routes that ignore it).
 */
export function apiFetch(path, options = {}) {
  const session = getSession()
  const headers = { ...options.headers }
  if (session) {
    headers.Authorization = `Bearer ${session.token}`
  }
  return fetch(apiUrl(path), { ...options, headers })
}
