import { useCallback, useEffect, useState } from 'react'
import { api, ApiError } from '../services/api'

export function useFetch<T>(path: string | null, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(Boolean(path))
  const [error, setError] = useState<string | null>(null)

  const reload = useCallback(async () => {
    if (!path) { setData(null); setLoading(false); return }
    setLoading(true); setError(null)
    try {
      setData(await api.get<T>(path))
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'The request could not be completed.')
    } finally {
      setLoading(false)
    }
  }, [path])

  useEffect(() => { reload() /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [path, ...deps])

  return { data, loading, error, reload, setData }
}

export function usePost<T>(path: string | null, body: unknown, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(Boolean(path))
  const [error, setError] = useState<string | null>(null)
  const key = JSON.stringify(body)

  const reload = useCallback(async () => {
    if (!path) { setData(null); setLoading(false); return }
    setLoading(true); setError(null)
    try {
      setData(await api.post<T>(path, JSON.parse(key)))
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'The analysis could not be completed.')
    } finally {
      setLoading(false)
    }
  }, [path, key])

  useEffect(() => { reload() /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [path, key, ...deps])

  return { data, loading, error, reload, setData }
}
