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
 * { token, profileId, profileName }. Nothing besides local storage cares about
 * this yet (write endpoints don't require it until #29) - it's stored now so
 * the login screen has somewhere to remember "who's using the app".
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
