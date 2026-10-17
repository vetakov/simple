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
  const rawUser = payload?.user || payload?.data?.user || payload?.data || payload
  if (!rawUser || typeof rawUser !== 'object' || Array.isArray(rawUser)) return rawUser

  // Keep the client tolerant of both snake_case API responses and the
  // camelCase shape used by a few integrations. The backend can add
  // organization metadata without requiring a frontend release.
  const rawOrganizations = rawUser.organizations
    || rawUser.orgs
    || payload?.organizations
    || payload?.data?.organizations
    || []
  const organizations = Array.isArray(rawOrganizations)
    ? rawOrganizations
      .filter((organization) => organization && typeof organization === 'object')
      .map((organization) => ({
        ...organization,
        id: organization.id ?? organization.organization_id ?? organization.slug ?? organization.name,
        name: organization.name || organization.title || organization.slug || 'Организация',
      }))
      .filter((organization) => organization.id !== undefined && organization.id !== null)
    : []
  const activeOrganization = rawUser.active_organization
    || rawUser.activeOrganization
    || payload?.active_organization
    || payload?.activeOrganization
  const activeOrganizationId = rawUser.active_organization_id
    ?? rawUser.activeOrganizationId
    ?? activeOrganization?.id
    ?? null

  return {
    ...rawUser,
    organizations,
    active_organization_id: activeOrganizationId,
  }
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
