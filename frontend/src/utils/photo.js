import { API_BASE_URL } from '../services/api'

export function resolvePhotoUrl(value, fallback = '/avatar-user-red.svg') {
  if (!value) return fallback
  if (/^(https?:|data:|blob:)/i.test(value)) return value
  if (value.startsWith('/data/')) return `${API_BASE_URL}${value}`
  return value
}
