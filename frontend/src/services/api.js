const isViteDevServer = ['48621', '5173'].includes(window.location.port)
const BASE_URL = import.meta.env.VITE_API_URL || (isViteDevServer ? 'http://127.0.0.1:48620' : window.location.origin)

function formatApiErrorDetail(detail) {
  if (!detail) return null
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail
      .map(item => item?.msg || item?.message || JSON.stringify(item))
      .filter(Boolean)
      .join(' ')
  }
  return detail.message || JSON.stringify(detail)
}

async function request(path, token, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  }
  if (token) {
    headers.Authorization = `Bearer ${token}`
  }
  const response = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers,
  })
  if (!response.ok) {
    let message = 'Erreur API'
    try {
      const payload = await response.json()
      message = formatApiErrorDetail(payload.detail) || message
    } catch (err) {
      message = response.statusText || message
    }
    throw new Error(message)
  }
  return response.json()
}

export function loginRequest(credentials) {
  return request('/login', null, {
    method: 'POST',
    body: JSON.stringify(credentials),
  })
}

export function fetchInventory(token) {
  return request('/inventory', token)
}

export function fetchStockItems(token) {
  return request('/stock-items', token)
}

export function fetchCurrentUser(token) {
  return request('/me', token)
}

export function updateCurrentUser(token, payload) {
  return request('/users/me', token, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export function uploadUserPhoto(token, payload) {
  return request('/users/photo', token, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function fetchUsers(token) {
  return request('/users', token)
}

export function createUser(token, payload) {
  return request('/users', token, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateUser(token, username, payload) {
  return request(`/users/${encodeURIComponent(username)}`, token, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export function deleteUser(token, username) {
  return request(`/users/${encodeURIComponent(username)}`, token, {
    method: 'DELETE',
  })
}

export function fetchForecast(token) {
  return request('/forecast', token)
}

export function fetchMovements(token) {
  return request('/movements', token)
}

export function fetchAuditLogs(token) {
  return request('/audit-logs', token)
}

export function submitEntry(token, payload) {
  return request('/entries', token, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function submitExit(token, payload) {
  return request('/exits', token, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function logoutRequest(token) {
  return request('/logout', token, {
    method: 'POST',
  })
}
