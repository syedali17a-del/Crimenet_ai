import { useEffect, useRef, useState } from 'react'
import { Icon } from '../shared/Icon'
import { useI18n } from '../../i18n/LanguageContext'
import { LANGS, LANGUAGE_META, type Lang } from '../../i18n'

/**
 * Language switcher for the authenticated shell.
 *
 * Changing language only re-renders: it does NOT sign the user out, reload the
 * page, clear the active case, reset filters or discard analysis results,
 * because the language lives in its own context and every page reads its
 * strings from that context at render time.
 */
export default function LanguageSwitcher({ compact = false }: { compact?: boolean }) {
  const { lang, setLang, t, meta } = useI18n()
  const [open, setOpen] = useState(false)
  const box = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const onDown = (e: MouseEvent) => {
      if (box.current && !box.current.contains(e.target as Node)) setOpen(false)
    }
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false) }
    document.addEventListener('mousedown', onDown)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDown)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  function pick(l: Lang) {
    setLang(l)
    setOpen(false)
  }

  return (
    <div ref={box} className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-label={t.nav.languageAria}
        aria-haspopup="listbox"
        aria-expanded={open}
        title={`${t.nav.currentLanguage}: ${meta.endonym}`}
        className="focus-ring flex items-center gap-1.5 rounded-lg border border-[rgba(147,194,251,0.6)] bg-white/80 px-2 py-1.5 text-[var(--color-text)] transition hover:bg-[var(--color-primary-soft)]"
      >
        <Icon name="globe" size={15} />
        {!compact && (
          <span lang={meta.locale} className="max-w-[92px] truncate text-[12.5px] font-semibold leading-normal">
            {meta.endonym}
          </span>
        )}
        <Icon name="chevron" size={12} className={open ? 'rotate-180 transition-transform' : 'transition-transform'} />
      </button>

      {open && (
        <div
          role="listbox"
          aria-label={t.nav.language}
          className="glass-solid absolute right-0 top-[calc(100%+8px)] z-50 w-[212px] rounded-xl p-1.5"
        >
          <p className="px-2 pb-1 pt-1 text-[10px] font-bold uppercase tracking-wider text-[var(--color-text-muted)]/55">
            {t.nav.language}
          </p>
          {LANGS.map((code) => {
            const m = LANGUAGE_META[code]
            const active = code === lang
            return (
              <button
                key={code}
                role="option"
                aria-selected={active}
                lang={m.locale}
                onClick={() => pick(code)}
                className={`focus-ring flex w-full items-center gap-2 rounded-lg px-2 py-2 text-left transition ${
                  active ? 'bg-[var(--color-primary)] text-white' : 'text-[var(--color-primary-deep)] hover:bg-[var(--color-primary-soft)]'
                }`}
              >
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-[13.5px] font-semibold leading-relaxed">{m.endonym}</span>
                  <span className={`block truncate text-[10.5px] font-medium ${active ? 'text-[var(--color-primary-soft)]' : 'text-[var(--color-text-muted)]/60'}`}>
                    {m.english}
                  </span>
                </span>
                {active && <Icon name="check" size={14} />}
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}
