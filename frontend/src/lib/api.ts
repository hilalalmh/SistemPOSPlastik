export interface ApiError {
  code: string
  message: string
  details?: unknown[]
}

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? '/api/v1'
const REFRESH_STORAGE_KEY = 'pos_refresh_token'

let accessToken: string | null = null
let onUnauthorized: (() => void) | null = null

export function setAccessToken(token: string | null) {
  accessToken = token
}

export function getRefreshToken() {
  return localStorage.getItem(REFRESH_STORAGE_KEY)
}

export function setRefreshToken(token: string | null) {
  if (token) localStorage.setItem(REFRESH_STORAGE_KEY, token)
  else localStorage.removeItem(REFRESH_STORAGE_KEY)
}

export function setUnauthorizedHandler(handler: () => void) {
  onUnauthorized = handler
}

export class RequestError extends Error implements ApiError {
  code: string
  details?: unknown[]
  status: number

  constructor(error: ApiError, status: number) {
    super(error.message)
    this.name = 'RequestError'
    this.code = error.code
    this.details = error.details
    this.status = status
  }
}

async function parseError(response: Response): Promise<RequestError> {
  let body: { error?: ApiError } | undefined
  try {
    body = await response.json()
  } catch {
    body = undefined
  }
  const error = body?.error ?? {
    code: 'UNKNOWN',
    message: `Permintaan gagal (${response.status}).`,
  }
  return new RequestError(error, response.status)
}

let refreshPromise: Promise<boolean> | null = null

async function tryRefresh(): Promise<boolean> {
  const refreshToken = getRefreshToken()
  if (!refreshToken) return false
  if (!refreshPromise) {
    refreshPromise = (async () => {
      try {
        const response = await fetch(`${API_BASE}/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refreshToken }),
        })
        if (!response.ok) return false
        const data = await response.json()
        accessToken = data.access_token
        setRefreshToken(data.refresh_token)
        return true
      } catch {
        return false
      } finally {
        refreshPromise = null
      }
    })()
  }
  return refreshPromise
}

export interface RequestOptions {
  method?: string
  body?: unknown
  headers?: Record<string, string>
  auth?: boolean
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, headers = {}, auth = true } = options

  const doFetch = async (): Promise<Response> => {
    const finalHeaders: Record<string, string> = { ...headers }
    if (body !== undefined) finalHeaders['Content-Type'] = 'application/json'
    if (auth && accessToken) finalHeaders.Authorization = `Bearer ${accessToken}`
    return fetch(`${API_BASE}${path}`, {
      method,
      headers: finalHeaders,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    })
  }

  let response = await doFetch()

  if (response.status === 401 && auth) {
    const refreshed = await tryRefresh()
    if (refreshed) {
      response = await doFetch()
    } else {
      onUnauthorized?.()
      throw await parseError(response)
    }
  }

  if (!response.ok) throw await parseError(response)
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}
