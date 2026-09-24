import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import {
  dictFor, isLang, lookup, makeFormatters, LANGUAGE_META,
  type Dict, type Formatters, type Lang,
} from './index'

const STORAGE_KEY = 'crimenet.lang'
/** Set once the user has explicitly chosen - gates the language screen. */
const CHOSEN_KEY = 'crimenet.lang.chosen'

interface LanguageValue {
  lang: Lang
  /** True only after an explicit user choice on the language screen. */
  chosen: boolean
  setLang: (l: Lang) => void
  /** Records the explicit first choice and unlocks the rest of the app. */
  chooseLang: (l: Lang) => void
  t: Dict
  fmt: Formatters
  meta: (typeof LANGUAGE_META)[Lang]
  /** Localise a backend token, falling back to a humanised form. */
  tok: (map: Record<string, string>, token: string | null | undefined, fallback?: string) => string
}

const Ctx = createContext<LanguageValue | null>(null)

function readStored(): { lang: Lang; chosen: boolean } {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    const chosen = localStorage.getItem(CHOSEN_KEY) === '1'
    if (isLang(raw)) return { lang: raw, chosen }
  } catch {
    /* storage unavailable - fall through to the default */
  }
  return { lang: 'en', chosen: false }
}

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [{ lang, chosen }, setState] = useState(readStored)

  // Keep <html lang> and the script class in sync so the CSS font stacks and
  // Indic line-height rules apply, and so screen readers announce correctly.
  useEffect(() => {
    const meta = LANGUAGE_META[lang]
    document.documentElement.lang = meta.locale
    document.documentElement.dataset.script = meta.script
    document.documentElement.classList.remove('lang-en', 'lang-ta', 'lang-hi')
    document.documentElement.classList.add(`lang-${lang}`)
  }, [lang])

  const setLang = useCallback((l: Lang) => {
    setState((s) => ({ ...s, lang: l }))
    try { localStorage.setItem(STORAGE_KEY, l) } catch { /* ignore */ }
  }, [])

  const chooseLang = useCallback((l: Lang) => {
    setState({ lang: l, chosen: true })
    try {
      localStorage.setItem(STORAGE_KEY, l)
      localStorage.setItem(CHOSEN_KEY, '1')
    } catch { /* ignore */ }
  }, [])

  const value = useMemo<LanguageValue>(() => ({
    lang,
    chosen,
    setLang,
    chooseLang,
    t: dictFor(lang),
    fmt: makeFormatters(lang),
    meta: LANGUAGE_META[lang],
    tok: lookup,
  }), [lang, chosen, setLang, chooseLang])

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useI18n(): LanguageValue {
  const v = useContext(Ctx)
  if (!v) throw new Error('useI18n must be used inside <LanguageProvider>')
  return v
}
