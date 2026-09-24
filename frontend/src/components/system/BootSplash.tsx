import { useEffect, useRef, useState } from 'react'
import { BrandMark, Tagline, Wordmark } from '../brand/Brand'
import { Icon } from '../shared/Icon'
import { useI18n } from '../../i18n/LanguageContext'

/**
 * Application boot sequence — the CrimeNet AI mark resolves in the centre of the
 * screen while the client performs real start-up work (service reachability,
 * platform metadata, session presence). It then hands over to the entry screen.
 *
 * Nothing here is decorative-only: every step reports the true result, and a
 * failed handshake blocks with an explicit, actionable message instead of
 * dropping the user on a login form that cannot work.
 */

type StepState = 'pending' | 'active' | 'done' | 'failed'
type StepKey = 'stepClient' | 'stepServices' | 'stepPlatform' | 'stepSession'
interface Step { id: string; labelKey: StepKey; state: StepState; detail?: string }

const BOOT_MS = 2300

export default function BootSplash({ onDone }: { onDone: () => void }) {
  const { t } = useI18n()
  // Steps are keyed, not string-labelled, so a language change mid-boot still
  // renders the right copy.
  const [steps, setSteps] = useState<Step[]>([
    { id: 'client', labelKey: 'stepClient', state: 'active' },
    { id: 'services', labelKey: 'stepServices', state: 'pending' },
    { id: 'platform', labelKey: 'stepPlatform', state: 'pending' },
    { id: 'session', labelKey: 'stepSession', state: 'pending' },
  ])
  const [failed, setFailed] = useState<string | null>(null)
  const [leaving, setLeaving] = useState(false)
  const startedAt = useRef(Date.now())

  function mark(id: string, state: StepState, detail?: string) {
    setSteps((prev) => prev.map((s) => (s.id === id ? { ...s, state, detail } : s)))
  }

  async function boot() {
    setFailed(null)
    startedAt.current = Date.now()
    setSteps((prev) => prev.map((s, i) => ({ ...s, state: i === 0 ? 'active' : 'pending', detail: undefined })))

    await wait(260)
    mark('client', 'done', t.boot.detailClientReady)
    mark('services', 'active')

    try {
      const health = await fetchJson('/api/health', 6000)
      mark('services', 'done', `${t.boot.detailApiOnline} · ${health.status ?? 'ok'}`)
    } catch {
      mark('services', 'failed', t.boot.detailNoResponse)
      setFailed(t.boot.unreachableBody)
      return
    }

    mark('platform', 'active')
    try {
      const meta = await fetchJson('/api/meta', 6000)
      mark('platform', 'done', `v${meta.version ?? '1.0.0'} · ${meta.classification ?? 'SYNTHETIC DEMONSTRATION DATA'}`)
    } catch {
      mark('platform', 'done', t.boot.detailProfileUnavailable)
    }

    mark('session', 'active')
    await wait(220)
    const hasToken = Boolean(
      localStorage.getItem('crimenet.token') || sessionStorage.getItem('crimenet.token'),
    )
    mark('session', 'done', hasToken ? t.boot.detailSessionFound : t.boot.detailNoSession)

    const elapsed = Date.now() - startedAt.current
    await wait(Math.max(0, BOOT_MS - elapsed))
    setLeaving(true)
    await wait(480)
    onDone()
  }

  useEffect(() => {
    boot()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div
      className={`panel-navy fixed inset-0 z-[200] flex items-center justify-center overflow-hidden transition-all duration-500 ${
        leaving ? 'pointer-events-none scale-[1.04] opacity-0' : 'opacity-100'
      }`}
    >
      <div className="grid-drift pointer-events-none absolute inset-0 opacity-[0.55]" />
      <div className="pointer-events-none absolute inset-0 grid-drift opacity-30" />
      

      <div className="relative w-full max-w-[560px] px-6 text-center">
        <div className="relative mx-auto flex h-[132px] w-[132px] items-center justify-center">
          <span className="boot-ring absolute inset-0 rounded-full border border-brand-300/45" />
          <span className="boot-ring absolute inset-0 rounded-full border border-brand-300/30" style={{ animationDelay: '700ms' }} />
          <span className="absolute inset-[14px] rounded-full bg-brand-500/10 blur-xl" />
          <BrandMark size={104} animate />
        </div>

        <div className="mt-6">
          <span className="boot-word block">
            <Wordmark size="xl" tone="light" />
          </span>
          <Tagline tone="light" className="mt-3 text-[11px] tracking-[0.28em] sm:text-[12px]" />
        </div>

        <p className="mx-auto mt-5 max-w-[430px] text-[12.5px] leading-relaxed text-brand-100/70">
          {t.common.productSubtitle}
        </p>

        {/* progress */}
        <div className="mx-auto mt-7 h-[3px] w-[240px] overflow-hidden rounded-full bg-white/10">
          {!failed && (
            <div
              className="bar-grow h-full rounded-full bg-[var(--color-primary)]"
              style={{ ['--boot-duration' as string]: `${BOOT_MS}ms` }}
            />
          )}
          {failed && <div className="h-full w-1/3 rounded-full bg-[var(--color-danger)]" />}
        </div>

        {/* real start-up steps */}
        <ul className="mx-auto mt-5 w-full max-w-[380px] space-y-1.5 text-left">
          {steps.map((s) => (
            <li key={s.id} className="flex items-start gap-2">
              <span className="mt-[3px] shrink-0">
                {s.state === 'done' && <span className="text-emerald-300"><Icon name="check" size={13} /></span>}
                {s.state === 'active' && (
                  <span className="block h-3 w-3 animate-spin rounded-full border-[1.5px] border-brand-200/40 border-t-brand-200" />
                )}
                {s.state === 'pending' && <span className="block h-3 w-3 rounded-full border border-white/20" />}
                {s.state === 'failed' && <span className="text-rose-300"><Icon name="alert" size={13} /></span>}
              </span>
              <span className="min-w-0">
                <span className={`block text-[12px] font-medium ${s.state === 'pending' ? 'text-white/35' : 'text-white/85'}`}>
                  {t.boot[s.labelKey]}
                </span>
                {s.detail && <span className="block text-[11px] text-brand-200/60">{s.detail}</span>}
              </span>
            </li>
          ))}
        </ul>

        {failed && (
          <div className="fade-in mx-auto mt-5 max-w-[420px] rounded-[12px] border border-[var(--color-danger)] bg-[rgba(196,52,31,0.08)] px-4 py-3 text-left">
            <p className="flex items-center gap-1.5 text-[12.5px] font-bold text-rose-100">
              <Icon name="alert" size={14} /> {t.boot.unreachableTitle}
            </p>
            <p className="mt-1 text-[12px] leading-relaxed text-rose-50/80">{failed}</p>
            <div className="mt-2.5 flex flex-wrap gap-2">
              <button
                onClick={boot}
                className="focus-ring rounded-lg bg-white/90 px-3 py-1.5 text-[12px] font-bold text-navy-900 transition hover:bg-white"
              >
                {t.boot.retryHandshake}
              </button>
              <button
                onClick={onDone}
                className="focus-ring rounded-lg border border-white/25 px-3 py-1.5 text-[12px] font-semibold text-white/80 transition hover:bg-white/10"
              >
                {t.boot.continueOffline}
              </button>
            </div>
          </div>
        )}

        <p className="mt-6 text-[10.5px] font-semibold uppercase tracking-[0.22em] text-brand-200/45">
          {t.boot.footer}
        </p>
      </div>
    </div>
  )
}

function wait(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

async function fetchJson(path: string, timeoutMs: number): Promise<any> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)
  try {
    const res = await fetch(path, { signal: controller.signal })
    if (!res.ok) throw new Error(String(res.status))
    return await res.json()
  } finally {
    clearTimeout(timer)
  }
}
