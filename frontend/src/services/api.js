const isViteDevServer = ['48621', '5173'].includes(window.location.port)
const defaultBackendHost = '127.0.0.1:48620'
const defaultBackendProtocol = window.location.protocol === 'https:' ? 'https:' : 'http:'
export const API_BASE_URL = import.meta.env.VITE_API_URL || (isViteDevServer ? `${defaultBackendProtocol}//${defaultBackendHost}` : window.location.origin)
const BASE_URL = API_BASE_URL

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
  const isFormData = options.body instanceof FormData
  const headers = {
    ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
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

export function fetchSerialRegistry(token) {
  return request('/serial-registry', token)
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

export function fetchStockPolicies(token) {
  return request('/stock-policies', token)
}

export function updateStockPolicy(token, equipmentType, payload) {
  return request(`/stock-policies?type=${encodeURIComponent(equipmentType)}`, token, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
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

export function importEntrySerialNumbers(token, payload) {
  const formData = new FormData()
  formData.append('type', payload.type)
  formData.append('file', payload.file)
  if (payload.notes) {
    formData.append('notes', payload.notes)
  }
  return request('/entries/serial-import', token, {
    method: 'POST',
    body: formData,
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
