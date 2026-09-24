import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { api, ApiError, setUnauthorizedHandler, tokenStore } from '../services/api'
import type { CaseOut, LoginResponse, UserProfile } from '../types'

type Toast = { id: number; kind: 'success' | 'error' | 'info'; title: string; message?: string }

interface AppState {
  user: UserProfile | null
  ready: boolean
  cases: CaseOut[]
  casesLoading: boolean
  /** non-null when the case list could not be fetched — pages must show this, not an empty state */
  casesError: string | null
  activeCase: string | null
  setActiveCase: (id: string | null) => void
  login: (userId: string, password: string, remember: boolean) => Promise<void>
  logout: () => void
  refreshCases: () => Promise<void>
  can: (permission: string) => boolean
  toasts: Toast[]
  notify: (kind: Toast['kind'], title: string, message?: string) => void
  dismiss: (id: number) => void
  classification: string
}

const Ctx = createContext<AppState | null>(null)
let toastSeq = 1

export function AppProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(() => tokenStore.getUser<UserProfile>())
  const [ready, setReady] = useState(false)
  const [cases, setCases] = useState<CaseOut[]>([])
  const [casesLoading, setCasesLoading] = useState(false)
  const [casesError, setCasesError] = useState<string | null>(null)
  const [activeCase, setActiveCaseState] = useState<string | null>(
    () => localStorage.getItem('crimenet.activeCase') || null,
  )
  const [toasts, setToasts] = useState<Toast[]>([])

  const notify = useCallback((kind: Toast['kind'], title: string, message?: string) => {
    const id = toastSeq++
    setToasts((t) => [...t, { id, kind, title, message }])
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 5200)
  }, [])
  const dismiss = useCallback((id: number) => setToasts((t) => t.filter((x) => x.id !== id)), [])

  const setActiveCase = useCallback((id: string | null) => {
    setActiveCaseState(id)
    if (id) localStorage.setItem('crimenet.activeCase', id)
    else localStorage.removeItem('crimenet.activeCase')
  }, [])

  const refreshCases = useCallback(async () => {
    setCasesLoading(true)
    try {
      const data = await api.get<CaseOut[]>('/api/cases')
      setCases(data)
      setCasesError(null)
      setActiveCaseState((current) => {
        if (current && data.some((c) => c.case_id === current)) return current
        return null
      })
    } catch (err) {
      if (!(err instanceof ApiError && err.status === 401)) {
        setCasesError(err instanceof Error ? err.message : 'The case list could not be loaded.')
        notify('error', 'Unable to load cases', err instanceof Error ? err.message : undefined)
      }
    } finally {
      setCasesLoading(false)
    }
  }, [notify])

  const logout = useCallback(() => {
    api.post('/api/auth/logout').catch(() => undefined)
    tokenStore.clear()
    setUser(null)
    setCases([])
    setActiveCase(null)
  }, [setActiveCase])

  useEffect(() => {
    setUnauthorizedHandler(() => {
      setUser(null)
      setCases([])
    })
  }, [])

  useEffect(() => {
    let cancelled = false
    async function bootstrap() {
      if (!tokenStore.get()) {
        // A cached profile without a token is a stale session - drop it so the
        // shell never renders against credentials the backend will reject.
        tokenStore.clear()
        setUser(null)
        setReady(true)
        return
      }
      try {
        const profile = await api.get<UserProfile>('/api/auth/me')
        if (cancelled) return
        setUser(profile)
        tokenStore.setUser(profile)
        await refreshCases()
      } catch {
        tokenStore.clear()
        setUser(null)
      } finally {
        if (!cancelled) setReady(true)
      }
    }
    bootstrap()
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const login = useCallback(
    async (userId: string, password: string, remember: boolean) => {
      const res = await api.post<LoginResponse>('/api/auth/login', {
        user_id: userId.trim(),
        password,
        remember,
      })
      tokenStore.set(res.access_token, remember)
      tokenStore.setUser(res.user)
      setUser(res.user)
      await refreshCases()
      notify('success', `Signed in as ${res.user.display_name}`, `Role: ${res.user.role}`)
    },
    [refreshCases, notify],
  )

  const can = useCallback(
    (permission: string) => Boolean(user?.permissions?.includes(permission)),
    [user],
  )

  const value = useMemo<AppState>(
    () => ({
      user, ready, cases, casesLoading, casesError, activeCase, setActiveCase, login, logout,
      refreshCases, can, toasts, notify, dismiss,
      classification: 'SYNTHETIC DEMONSTRATION DATA',
    }),
    [user, ready, cases, casesLoading, casesError, activeCase, setActiveCase, login, logout, refreshCases, can, toasts, notify, dismiss],
  )

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useApp(): AppState {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error('useApp must be used inside AppProvider')
  return ctx
}
