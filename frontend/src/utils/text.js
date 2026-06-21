export function normalizeBusinessText(value) {
  if (!value) return value
  return String(value).replaceAll('Depot IT', 'Dépôt IT')
}
