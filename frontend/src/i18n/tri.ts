/**
 * CrimeNet AI - localisation core.
 *
 * Design rules:
 *  1. Every domain dictionary declares English first, derives a TYPE from it,
 *     and then requires Tamil and Hindi to satisfy exactly that type. A missing
 *     or misspelled key is therefore a COMPILE ERROR, not a runtime "??key??".
 *  2. Interpolation is done with plain typed functions, so there is no runtime
 *     key-path lookup that can fail.
 *  3. No new dependency: this is plain TypeScript + React context, inside the
 *     declared CrimeNet AI stack.
 */

export const LANGS = ['en', 'ta', 'hi'] as const
export type Lang = (typeof LANGS)[number]

/** A domain dictionary supplied in all three languages. */
export type Tri<T> = { en: T; ta: T; hi: T }

export const LANGUAGE_META: Record<Lang, {
  /** Name written in its own script - never translated. */
  endonym: string
  /** Name in English, for accessibility labels. */
  english: string
  /** BCP-47 tag used for Intl formatting and the <html lang> attribute. */
  locale: string
  /** Short code shown in the compact switcher. */
  short: string
  script: 'latin' | 'tamil' | 'devanagari'
}> = {
  en: { endonym: 'English', english: 'English', locale: 'en-IN', short: 'EN', script: 'latin' },
  ta: { endonym: 'தமிழ்', english: 'Tamil', locale: 'ta-IN', short: 'தமிழ்', script: 'tamil' },
  hi: { endonym: 'हिन्दी', english: 'Hindi', locale: 'hi-IN', short: 'हिन्दी', script: 'devanagari' },
}

export function isLang(v: unknown): v is Lang {
  return typeof v === 'string' && (LANGS as readonly string[]).includes(v)
}
