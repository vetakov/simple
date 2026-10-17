const API_BASE = (import.meta.env.VITE_API_URL || '/api').replace(/\/$/, '')

export class ApiError extends Error {
  constructor(message, status = 0) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function request(path, options = {}) {
  const token = localStorage.getItem('pulse.accessToken')
  const headers = new Headers(options.headers || {})
  if (options.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
  if (token) headers.set('Authorization', `Bearer ${token}`)

  let response
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers,
      credentials: 'include',
    })
  } catch {
    throw new ApiError('Не удалось подключиться к серверу')
  }

  const contentType = response.headers.get('content-type') || ''
  const payload = contentType.includes('application/json')
    ? await response.json().catch(() => ({}))
    : await response.text().catch(() => '')

  if (!response.ok) {
    const message = typeof payload === 'object' && payload !== null
      ? payload.detail || payload.message || payload.error
      : payload
    throw new ApiError(message || `Ошибка запроса (${response.status})`, response.status)
  }

  return payload
}

function normalizeUser(payload) {
  return payload?.user || payload?.data?.user || payload?.data || payload
}

export async function signIn(email, password) {
  const payload = await request('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })
  const token = payload?.access_token || payload?.token || payload?.data?.access_token
  if (token) localStorage.setItem('pulse.accessToken', token)
  return { user: normalizeUser(payload), token }
}

export async function currentUser() {
  const payload = await request('/auth/me')
  return normalizeUser(payload)
}

export async function dashboard() {
  const payload = await request('/dashboard')
  return payload?.data || payload
}

export async function signOut() {
  try {
    await request('/auth/logout', { method: 'POST' })
  } catch {
    // Clearing the local session is enough when the API does not expose logout.
  }
  localStorage.removeItem('pulse.accessToken')
}
