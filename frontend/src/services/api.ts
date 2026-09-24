/**
 * API client - single place where the JWT is attached and backend errors are
 * converted into user-friendly messages (raw stack traces are never surfaced).
 */
const TOKEN_KEY = 'crimenet.token'
const USER_KEY = 'crimenet.user'
const REMEMBER_KEY = 'crimenet.remember'

export class ApiError extends Error {
  status: number
  code: string
  constructor(message: string, status: number, code = 'ERROR') {
    super(message)
    this.status = status
    this.code = code
  }
}

function store(): Storage {
  return localStorage.getItem(REMEMBER_KEY) === '1' ? localStorage : sessionStorage
}

export const tokenStore = {
  get(): string | null {
    return localStorage.getItem(TOKEN_KEY) || sessionStorage.getItem(TOKEN_KEY)
  },
  set(token: string, remember: boolean) {
    localStorage.setItem(REMEMBER_KEY, remember ? '1' : '0')
    store().setItem(TOKEN_KEY, token)
  },
  clear() {
    localStorage.removeItem(TOKEN_KEY)
    sessionStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
    sessionStorage.removeItem(USER_KEY)
  },
  getUser<T>(): T | null {
    const raw = localStorage.getItem(USER_KEY) || sessionStorage.getItem(USER_KEY)
    try {
      return raw ? (JSON.parse(raw) as T) : null
    } catch {
      return null
    }
  },
  setUser(user: unknown) {
    store().setItem(USER_KEY, JSON.stringify(user))
  },
}

let onUnauthorized: (() => void) | null = null
export function setUnauthorizedHandler(fn: () => void) {
  onUnauthorized = fn
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = tokenStore.get()
  const headers = new Headers(init.headers || {})
  if (token) headers.set('Authorization', `Bearer ${token}`)
  if (init.body && !(init.body instanceof FormData)) headers.set('Content-Type', 'application/json')

  let res: Response
  try {
    res = await fetch(path, { ...init, headers })
  } catch {
    throw new ApiError('Cannot reach the CrimeNet AI analytical services. Check that the backend is running.', 0, 'NETWORK')
  }

  if (res.status === 401) {
    tokenStore.clear()
    onUnauthorized?.()
    const body = await res.json().catch(() => ({ detail: 'Session expired. Please sign in again.' }))
    throw new ApiError(body.detail || 'Session expired. Please sign in again.', 401, 'UNAUTHENTICATED')
  }

  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new ApiError(
      (body && (body.detail || body.message)) || `Request failed (${res.status}).`,
      res.status,
      (body && body.code) || 'ERROR',
    )
  }
  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}

export const api = {
  get: <T,>(path: string) => request<T>(path),
  post: <T,>(path: string, body?: unknown) =>
    request<T>(path, { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body) }),
  patch: <T,>(path: string, body?: unknown) =>
    request<T>(path, { method: 'PATCH', body: body === undefined ? undefined : JSON.stringify(body) }),
  upload: <T,>(path: string, form: FormData) => request<T>(path, { method: 'POST', body: form }),
}
