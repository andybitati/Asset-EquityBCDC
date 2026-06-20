const BASE_URL = 'http://127.0.0.1:8000'

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
    throw new Error('Erreur API')
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

export function fetchForecast(token) {
  return request('/forecast', token)
}

export function fetchMovements(token) {
  return request('/movements', token)
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
