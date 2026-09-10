const SERVER_URL_KEY = 'serverUrl'

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
