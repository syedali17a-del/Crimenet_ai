import { useState } from 'react'
import { BrandMark, Tagline, Wordmark } from '../components/brand/Brand'
import { Icon } from '../components/shared/Icon'
import { LANGS, LANGUAGE_META, type Lang } from '../i18n'
import { useI18n } from '../i18n/LanguageContext'

/**
 * FIRST screen of the application.
 *
 * The user must explicitly choose a language before the login page is shown.
 * Each card is written in its own script so it is readable to a speaker of
 * that language without them having to understand English first.
 */
export default function LanguageSelect() {
  const { lang, chooseLang, setLang, t } = useI18n()
  const [hover, setHover] = useState<Lang | null>(null)

  // Sub-labels are intentionally rendered in the card's OWN language, so a
  // Tamil speaker reads Tamil on the Tamil card regardless of current state.
  const SUB: Record<Lang, string> = {
    en: 'Continue in English',
    ta: 'தமிழில் தொடரவும்',
    hi: 'हिन्दी में जारी रखें',
  }
  const TITLE: Record<Lang, string> = {
    en: 'Select Your Language',
    ta: 'உங்கள் மொழியைத் தேர்ந்தெடுக்கவும்',
    hi: 'अपनी भाषा चुनें',
  }

  return (
    <div className="relative flex min-h-screen w-full items-center justify-center overflow-hidden px-4 py-8">
      <div className="grid-drift pointer-events-none absolute inset-0 opacity-[0.35]" />
      <svg aria-hidden viewBox="0 0 100 100" preserveAspectRatio="none" className="pointer-events-none absolute inset-0 h-full w-full opacity-40">
        <defs>
          <linearGradient id="cn-lang-line" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#1450C4" stopOpacity="0.28" />
            <stop offset="100%" stopColor="#2FA7DB" stopOpacity="0.20" />
          </linearGradient>
        </defs>
        <g stroke="url(#cn-lang-line)" strokeWidth="0.14" fill="none">
          <path d="M4 22 L22 12 L34 40 L18 58 L6 44 Z" />
          <path d="M34 40 L58 26 L76 44 L64 70 L40 74 Z" />
          <path d="M76 44 L94 30 M94 70 L64 70 M22 12 L58 26 M18 58 L40 74 M6 44 L4 22 M34 40 L40 74" />
        </g>
        <g fill="#1450C4" fillOpacity="0.18">
          <circle cx="4" cy="22" r="1" /><circle cx="22" cy="12" r="1" /><circle cx="34" cy="40" r="1.2" />
          <circle cx="18" cy="58" r="1" /><circle cx="6" cy="44" r="1" /><circle cx="58" cy="26" r="1.2" />
          <circle cx="76" cy="44" r="1.2" /><circle cx="64" cy="70" r="1" /><circle cx="40" cy="74" r="1" />
          <circle cx="94" cy="30" r="1" /><circle cx="94" cy="70" r="1" />
        </g>
      </svg>
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(680px_400px_at_50%_45%,rgba(255,255,255,0.9)_0%,rgba(255,255,255,0.4)_60%,rgba(244,247,252,0)_100%)]" />

      <div className="relative w-full max-w-[860px]">
        {/* brand */}
        <div className="rise-in flex flex-col items-center text-center">
          <BrandMark size={72} animate />
          <div className="mt-4">
            <Wordmark size="xl" />
            <Tagline className="mt-2 text-[10.5px] tracking-[0.2em]" />
          </div>
        </div>

        {/* heading - shown in all three scripts so nobody is excluded */}
        <div className="rise-in rise-in-1 mt-8 text-center">
          <h1 className="page-title sm:text-[30px]">
            {TITLE[lang]}
          </h1>
          <p className="mx-auto mt-2 max-w-[520px] text-[13.5px] leading-relaxed text-[var(--color-text-muted)]">
            {t.auth.chooseLanguageHint}
          </p>
        </div>

        {/* cards - stack on mobile, three across from sm upward */}
        <div className="rise-in rise-in-2 mt-7 grid grid-cols-1 gap-3 sm:grid-cols-3 sm:gap-4">
          {LANGS.map((code) => {
            const meta = LANGUAGE_META[code]
            const active = lang === code
            return (
              <button
                key={code}
                type="button"
                lang={meta.locale}
                onMouseEnter={() => { setHover(code); setLang(code) }}
                onFocus={() => { setHover(code); setLang(code) }}
                onMouseLeave={() => setHover(null)}
                onClick={() => chooseLang(code)}
                aria-label={`${meta.english} — ${meta.endonym}`}
                className={`focus-ring group relative flex min-h-[168px] flex-col items-center justify-center gap-2 overflow-hidden rounded-[22px] px-5 py-7 text-center transition-all duration-200 ${
                  active
                    ? 'bg-[var(--color-primary)] text-white shadow-[0_20px_40px_-24px_rgba(20,80,196,0.85)]'
                    : 'surface-solid text-[var(--color-text)] hover:-translate-y-1 hover:border-[var(--color-primary)]'
                }`}
              >
                <span
                  className={`absolute right-3 top-3 transition-opacity ${active ? 'opacity-100' : 'opacity-0'}`}
                >
                  <Icon name="check" size={17} />
                </span>

                <span
                  className={`text-[30px] font-extrabold leading-[1.5] tracking-tight sm:text-[34px] ${
                    active ? 'text-white' : 'text-[var(--color-primary-deep)]'
                  }`}
                >
                  {meta.endonym}
                </span>
                <span
                  className={`text-[12.5px] font-semibold leading-relaxed ${
                    active ? 'text-white/85' : 'text-[var(--color-text-muted)]'
                  }`}
                >
                  {SUB[code]}
                </span>
                <span
                  className={`mt-1 text-[10px] font-bold uppercase tracking-[0.18em] ${
                    active ? 'text-white/75' : 'text-[var(--color-primary)]'
                  }`}
                >
                  {meta.english}
                </span>

                <span
                  className={`pointer-events-none absolute inset-x-6 bottom-4 h-[2px] rounded-full bg-white/50 transition-transform duration-200 ${
                    hover === code && !active ? 'scale-x-100' : 'scale-x-0'
                  }`}
                />
              </button>
            )
          })}
        </div>

        {/* continue */}
        <div className="rise-in rise-in-3 mt-6 flex flex-col items-center gap-3">
          <button
            type="button"
            onClick={() => chooseLang(lang)}
            className="focus-ring inline-flex items-center gap-2 rounded-[12px] bg-[var(--color-primary)] px-6 py-3 text-[14px] font-semibold text-white transition hover:bg-[#0F3FA4]"
          >
            {t.auth.continue}
            <Icon name="arrowRight" size={16} />
          </button>
          <p className="max-w-[460px] text-center text-[11.5px] leading-relaxed text-[var(--color-text-muted)]">
            {t.auth.chooseLanguageFoot}
          </p>
        </div>

        <p className="mt-7 text-center text-[10px] font-semibold uppercase tracking-[0.18em] text-[var(--color-text-muted)]">
          {t.common.classificationBanner}
        </p>
      </div>
    </div>
  )
}
