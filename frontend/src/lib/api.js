const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

export async function requestJson(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, options)
  const text = await response.text()
  if (!response.ok) {
    throw new Error(text || `HTTP ${response.status}`)
  }
  return text ? JSON.parse(text) : null
}

export { API_BASE }
