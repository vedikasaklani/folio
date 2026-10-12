const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
const TOKEN_KEY = 'folio_token'

export const getToken = () => localStorage.getItem(TOKEN_KEY)

export function setToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token)
  else localStorage.removeItem(TOKEN_KEY)
}

// Returns parsed JSON (null for 204). Throws an Error with .status and .data on non-2xx.
export async function api(path, { method = 'GET', body } = {}) {
  const token = getToken()
  const res = await fetch(BASE + path, {
    method,
    headers: {
      ...(body && { 'Content-Type': 'application/json' }),
      ...(token && { Authorization: `Token ${token}` }),
    },
    body: body && JSON.stringify(body),
  })
  const data = res.status === 204 ? null : await res.json().catch(() => null)
  if (res.status === 401) setToken(null) // dead token: forget it so the UI falls back to login
  if (!res.ok) throw Object.assign(new Error(`HTTP ${res.status}`), { status: res.status, data })
  return data
}
