import { LANGUAGE_META, type Lang } from './tri'
import { common } from './strings/common'
import { nav } from './strings/nav'
import { auth } from './strings/auth'
import { boot } from './strings/boot'
import { pages } from './strings/pages'
import { dashboard } from './strings/dashboard'
import { cases } from './strings/cases'
import { evidence } from './strings/evidence'
import { analysis } from './strings/analysis'
import { reasoning } from './strings/reasoning'
import { tokens } from './strings/tokens'

export type { Lang } from './tri'
export { LANGS, LANGUAGE_META, isLang } from './tri'

/** The full dictionary for one language. */
export function buildDict(lang: Lang) {
  return {
    common: common[lang],
    nav: nav[lang],
    auth: auth[lang],
    boot: boot[lang],
    pages: pages[lang],
    dashboard: dashboard[lang],
    cases: cases[lang],
    evidence: evidence[lang],
    analysis: analysis[lang],
    reasoning: reasoning[lang],
    tokens: tokens[lang],
  }
}

export type Dict = ReturnType<typeof buildDict>

const CACHE = new Map<Lang, Dict>()
export function dictFor(lang: Lang): Dict {
  let d = CACHE.get(lang)
  if (!d) { d = buildDict(lang); CACHE.set(lang, d) }
  return d
}

/* ------------------------------------------------------------------ *
 * Token lookup with a safe fallback.
 *
 * If the backend ever emits a token this build does not know about, we
 * humanise the raw token ("RELATIONSHIPS_CANDIDATE" -> "Relationships
 * candidate") instead of rendering an empty cell or a key name. The UI
 * therefore degrades gracefully rather than breaking.
 * ------------------------------------------------------------------ */
export function humanise(token: string): string {
  if (!token) return ''
  return token
    .replace(/[_-]+/g, ' ')
    .toLowerCase()
    .replace(/^./, (c) => c.toUpperCase())
}

export function lookup(
  map: Record<string, string>,
  token: string | null | undefined,
  fallback = '',
): string {
  if (token == null || token === '') return fallback
  return map[token] ?? map[token.toUpperCase()] ?? humanise(token)
}

/* ------------------------------------------------------------------ *
 * Locale-aware formatting.
 *
 * Identifiers are deliberately NOT routed through here: case ids,
 * evidence ids, entity ids, registrations, phone numbers and hashes are
 * printed verbatim everywhere, in every language.
 * ------------------------------------------------------------------ */
export function makeFormatters(lang: Lang) {
  const locale = LANGUAGE_META[lang].locale

  const parse = (v: string | number | Date | null | undefined): Date | null => {
    if (v == null || v === '') return null
    const d = v instanceof Date ? v : new Date(v)
    return Number.isNaN(d.getTime()) ? null : d
  }

  return {
    locale,
    /** 10 August 2026 / 10 ஆகஸ்ட் 2026 / 10 अगस्त 2026 */
    date(v: string | number | Date | null | undefined, fallback = '—'): string {
      const d = parse(v)
      if (!d) return fallback
      return new Intl.DateTimeFormat(locale, {
        day: 'numeric', month: 'long', year: 'numeric',
      }).format(d)
    },
    dateShort(v: string | number | Date | null | undefined, fallback = '—'): string {
      const d = parse(v)
      if (!d) return fallback
      return new Intl.DateTimeFormat(locale, {
        day: '2-digit', month: 'short', year: 'numeric',
      }).format(d)
    },
    dateTime(v: string | number | Date | null | undefined, fallback = '—'): string {
      const d = parse(v)
      if (!d) return fallback
      return new Intl.DateTimeFormat(locale, {
        day: '2-digit', month: 'short', year: 'numeric',
        hour: '2-digit', minute: '2-digit',
      }).format(d)
    },
    time(v: string | number | Date | null | undefined, fallback = '—'): string {
      const d = parse(v)
      if (!d) return fallback
      return new Intl.DateTimeFormat(locale, { hour: '2-digit', minute: '2-digit' }).format(d)
    },
    number(v: number | null | undefined, digits = 0, fallback = '—'): string {
      if (v == null || Number.isNaN(v)) return fallback
      return new Intl.NumberFormat(locale, {
        minimumFractionDigits: digits, maximumFractionDigits: digits,
      }).format(v)
    },
    /** 0.92 -> 92% */
    percent(v: number | null | undefined, digits = 0, fallback = '—'): string {
      if (v == null || Number.isNaN(v)) return fallback
      return new Intl.NumberFormat(locale, {
        style: 'percent', minimumFractionDigits: digits, maximumFractionDigits: digits,
      }).format(v)
    },
    /** Joins a list the way the language does ("a, b and c"). */
    list(items: string[]): string {
      const clean = items.filter(Boolean)
      if (clean.length === 0) return ''
      try {
        return new Intl.ListFormat(locale, { style: 'long', type: 'conjunction' }).format(clean)
      } catch {
        return clean.join(', ')
      }
    },
  }
}

export type Formatters = ReturnType<typeof makeFormatters>

/* ------------------------------------------------------------------ *
 * Status resolution.
 *
 * A status string arriving from the backend can belong to any of several
 * vocabularies (verification, integrity, processing, corroboration verdict,
 * case state). Rather than force every call site to know which, we try each
 * vocabulary in turn and fall back to a humanised token.
 * ------------------------------------------------------------------ */
export function resolveStatus(tk: Dict['tokens'], status?: string | null): string {
  const s = (status ?? '').trim()
  if (!s) return ''
  const maps: Record<string, string>[] = [
    tk.verificationStatus, tk.integrityStatus, tk.processingStatus,
    tk.leadStatus, tk.caseStatus, tk.supportLevel,
  ]
  for (const m of maps) {
    const hit = m[s] ?? m[s.toUpperCase()]
    if (hit) return hit
  }
  return humanise(s)
}

/**
 * "INSUFFICIENT EVIDENCE: no timestamped events available for this scope."
 * -> localised sentence, or the original text when the reason is not one we
 * have a translation for (never silently dropped).
 */
export function resolveInsufficient(tk: Dict['tokens'], message?: string | null): string {
  const raw = (message ?? '').trim()
  if (!raw) return ''
  const marker = 'INSUFFICIENT EVIDENCE'
  const idx = raw.toUpperCase().indexOf(marker)
  if (idx === -1) return raw
  const head = tk.leadStatus['INSUFFICIENT EVIDENCE']
  const tail = raw.slice(idx + marker.length).replace(/^[:\s-]+/, '').trim()
  if (!tail) return head
  const known = tk.insufficientReason[tail as keyof typeof tk.insufficientReason]
  return known ? `${head}: ${known}` : `${head}: ${tail}`
}
