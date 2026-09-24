import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApp } from '../state/AppContext'
import { api, ApiError } from '../services/api'
import { Icon } from '../components/shared/Icon'
import { BrandMark, Tagline, Wordmark } from '../components/brand/Brand'
import { Button, Field, TextInput } from '../components/shared/ui'
import LanguageSwitcher from '../components/layout/LanguageSwitcher'
import { useI18n } from '../i18n/LanguageContext'

/* ============================================================================
   LOGIN — centred glass card over a faint network line pattern.

   The pattern is a static, deterministic SVG of a link graph (nodes + edges).
   It is drawn at low opacity behind the card and nothing else competes with it.
   The demo-account list and the SYNTHETIC DEMONSTRATION DATA disclosure are the
   exact same copy as before, in the same place in the flow — the sign-in screen
   must never look like a production system or present synthetic identities as
   real people.
   ============================================================================ */

interface DemoAccount { user_id: string; role: string; password: string; display_name?: string; case_access?: string[] }

/** Deterministic node/edge layout — no randomness, so the backdrop never jumps. */
const NET_NODES: Array<[number, number, number]> = [
  [6, 18, 3.2], [16, 34, 2.4], [13, 60, 4.0], [5, 78, 2.6], [26, 12, 2.2], [31, 44, 3.4],
  [24, 72, 2.4], [38, 26, 2.8], [44, 58, 2.2], [36, 86, 3.0], [52, 16, 3.6], [58, 40, 2.4],
  [50, 68, 2.6], [66, 22, 2.2], [72, 48, 3.4], [64, 78, 2.4], [80, 30, 2.8], [88, 54, 2.4],
  [78, 72, 3.0], [92, 20, 2.2], [94, 80, 2.6], [10, 46, 2.2], [30, 58, 2.0], [46, 84, 2.0],
  [70, 62, 2.0], [86, 38, 2.0],
]
const NET_EDGES: Array<[number, number]> = [
  [0, 1], [0, 4], [1, 2], [1, 21], [2, 3], [2, 6], [3, 6], [4, 7], [5, 7], [5, 8],
  [5, 21], [6, 10], [7, 10], [8, 9], [8, 12], [9, 12], [10, 11], [11, 13], [11, 14],
  [12, 14], [12, 15], [13, 16], [14, 16], [14, 20], [15, 17], [15, 19], [16, 17],
  [17, 18], [18, 20], [19, 20], [22, 1], [22, 8], [23, 9], [24, 18], [25, 14],
]

function NetworkBackdrop() {
  return (
    <svg
      aria-hidden
      viewBox="0 0 100 100"
      preserveAspectRatio="none"
      className="pointer-events-none absolute inset-0 h-full w-full"
      style={{ opacity: 0.5 }}
    >
      <defs>
        <linearGradient id="cn-login-line" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#1450C4" stopOpacity="0.30" />
          <stop offset="100%" stopColor="#2FA7DB" stopOpacity="0.22" />
        </linearGradient>
      </defs>
      <g stroke="url(#cn-login-line)" strokeWidth="0.14">
        {NET_EDGES.map(([a, b], i) => (
          <line key={i} x1={NET_NODES[a][0]} y1={NET_NODES[a][1]} x2={NET_NODES[b][0]} y2={NET_NODES[b][1]} />
        ))}
      </g>
      <g fill="#1450C4" fillOpacity="0.22">
        {NET_NODES.map(([x, y, r], i) => (
          <circle key={i} cx={x} cy={y} r={r * 0.16} />
        ))}
      </g>
    </svg>
  )
}

export default function Login() {
  const { login } = useApp()
  const { t, fmt, tok } = useI18n()
  const navigate = useNavigate()
  const [userId, setUserId] = useState('')
  const [password, setPassword] = useState('')
  const [remember, setRemember] = useState(true)
  const [showPassword, setShowPassword] = useState(false)
  const [capsLock, setCapsLock] = useState(false)
  const [busy, setBusy] = useState(false)
  const [step, setStep] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [accounts, setAccounts] = useState<DemoAccount[]>([])
  const [online, setOnline] = useState<'checking' | 'online' | 'offline'>('checking')
  const [clock, setClock] = useState(() => new Date())
  const stepTimer = useRef<number | null>(null)

  async function probe() {
    setOnline('checking')
    try {
      const res = await fetch('/api/health')
      setOnline(res.ok ? 'online' : 'offline')
      if (res.ok) {
        const roles = await api.get<{ demo_accounts: DemoAccount[] }>('/api/auth/roles')
        setAccounts(roles.demo_accounts || [])
      }
    } catch {
      setOnline('offline')
      setAccounts([])
    }
  }

  useEffect(() => { probe() }, [])
  useEffect(() => {
    const id = setInterval(() => setClock(new Date()), 30_000)
    return () => clearInterval(id)
  }, [])
  useEffect(() => () => { if (stepTimer.current) window.clearInterval(stepTimer.current) }, [])

  // Locale-aware timestamp: en-IN / ta-IN / hi-IN come from the formatters.
  const stamp = useMemo(() => fmt.dateTime(clock), [clock, fmt])

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    if (!userId.trim() || !password) {
      setError(t.auth.bothFieldsRequired)
      return
    }
    setBusy(true)
    setStep(0)
    stepTimer.current = window.setInterval(() => setStep((s) => Math.min(s + 1, t.auth.signInSteps.length - 1)), 420)
    try {
      await login(userId, password, remember)
      navigate('/dashboard', { replace: true })
    } catch (err) {
      const message = err instanceof ApiError
        ? (err.code === 'NETWORK' ? t.auth.backendUnreachable : err.message)
        : t.auth.signInFailed
      setError(message)
      if (err instanceof ApiError && err.code === 'NETWORK') setOnline('offline')
    } finally {
      if (stepTimer.current) window.clearInterval(stepTimer.current)
      setBusy(false)
    }
  }

  return (
    <div className="relative min-h-screen w-full overflow-hidden px-4 py-6 sm:px-6">
      {/* faint network line pattern — the only decoration on this screen */}
      <div className="pointer-events-none absolute inset-0">
        <div className="grid-drift absolute inset-0 opacity-[0.35]" />
        <NetworkBackdrop />
      </div>
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(760px_420px_at_50%_38%,rgba(255,255,255,0.88)_0%,rgba(255,255,255,0.35)_55%,rgba(244,247,252,0)_100%)]" />

      <div className="relative mx-auto flex min-h-[calc(100vh-48px)] w-full max-w-[1160px] flex-col items-center justify-center">
        <div className="mb-4 flex w-full max-w-[520px] items-center justify-between gap-3">
          <div className="flex items-center gap-3 sm:hidden">
            <BrandMark size={38} />
            <Wordmark size="md" />
          </div>
          <div className="ml-auto flex items-center gap-2">
            <span className="hidden text-[10.5px] font-semibold uppercase tracking-[0.16em] text-[var(--color-text-muted)] sm:block">
              {t.common.classificationBanner}
            </span>
            {/* BUG 3: no `compact` here — an icon-only globe gave the first screen's
                only control no readable label. The full control shows the language name. */}
            <LanguageSwitcher />
          </div>
        </div>

        {/* ── the centred glass card ─────────────────────────────────────── */}
        <section className="glass rise-in w-full max-w-[520px] px-6 py-6 sm:px-7 sm:py-7">
          <div className="hidden items-center gap-3.5 sm:flex">
            <BrandMark size={46} />
            <div className="min-w-0">
              <Wordmark size="lg" />
              <Tagline className="mt-1 text-[10px] tracking-[0.18em]" />
            </div>
          </div>

          <div className="mt-5 flex items-start gap-2.5">
            <span className="surface-soft rounded-[10px] p-2 text-[var(--color-primary)]">
              <Icon name="lock" size={17} />
            </span>
            <div>
              <h1 className="text-[18px] font-semibold leading-tight text-[var(--color-primary-deep)]">{t.auth.secureAccess}</h1>
              <p className="text-[12px] text-[var(--color-text-muted)]">{t.auth.secureAccessSub}</p>
            </div>
          </div>

          <ServiceState state={online} onRetry={probe} />

          <form onSubmit={submit} className="mt-4 space-y-4" noValidate>
            <Field label={t.auth.userIdLabel} required>
              <TextInput
                value={userId}
                onChange={(e) => setUserId(e.target.value.toUpperCase())}
                placeholder="INV-2201"
                autoComplete="username"
                autoFocus
                className="mono-id tracking-wide"
              />
            </Field>

            <Field label={t.auth.passwordLabel} required>
              <div className="relative">
                <TextInput
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  onKeyUp={(e) => setCapsLock(e.getModifierState?.('CapsLock') ?? false)}
                  placeholder="••••••••••"
                  autoComplete="current-password"
                  className="pr-11"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((s) => !s)}
                  aria-label={showPassword ? t.auth.hidePassword : t.auth.showPassword}
                  className="focus-ring absolute right-1.5 top-1/2 -translate-y-1/2 rounded-lg p-1.5 text-[var(--color-text-muted)] transition hover:bg-[var(--color-primary-soft)]"
                >
                  <Icon name={showPassword ? 'close' : 'eye'} size={15} />
                </button>
              </div>
            </Field>

            {capsLock && (
              <p className="flex items-center gap-1.5 text-[11.5px] font-semibold text-[var(--color-warning)]">
                <Icon name="alert" size={13} /> {t.auth.capsLockOn}
              </p>
            )}

            <div className="flex items-center justify-between gap-2">
              <label className="flex cursor-pointer items-center gap-2 text-[12.5px] font-medium text-[var(--color-text)]">
                <input
                  type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)}
                  className="focus-ring h-4 w-4 rounded border-[var(--color-border)] accent-[var(--color-primary)]"
                />
                {t.auth.rememberSession}
              </label>
              <span className="text-[11px] font-semibold text-[var(--color-text-muted)]">{t.auth.sessionLength}</span>
            </div>

            {error && (
              <div role="alert" className="fade-in flex items-start gap-2 rounded-[12px] border border-[var(--color-danger)] bg-[rgba(196,52,31,0.06)] px-3 py-2.5 text-[12.5px] text-[var(--color-danger)]">
                <span className="mt-0.5 shrink-0"><Icon name="alert" size={15} /></span>
                <span>{error}</span>
              </div>
            )}

            <Button type="submit" variant="primary" className="w-full py-3 text-[14px]" loading={busy} icon={busy ? undefined : 'arrowRight'}>
              {busy ? t.auth.signInSteps[step] + '…' : t.auth.signIn}
            </Button>

            {busy && (
              <div className="h-[3px] w-full overflow-hidden rounded-full bg-[var(--color-primary-soft)]">
                <div
                  className="h-full rounded-full bg-[var(--color-primary)] transition-all duration-500"
                  style={{ width: `${((step + 1) / t.auth.signInSteps.length) * 100}%` }}
                />
              </div>
            )}
          </form>

          {/* ---- demo accounts (unchanged list, unchanged copy) ---------- */}
          <div className="mt-6 border-t border-[var(--color-border)] pt-4">
            <div className="mb-2 flex items-center justify-between gap-2">
              <p className="section-header !text-[12px]">{t.auth.demoAccounts}</p>
              <span className="text-[10.5px] font-semibold text-[var(--color-text-muted)]">{t.auth.demoAccountsHint}</span>
            </div>

            {accounts.length === 0 && (
              <p className="rounded-[12px] border border-dashed border-[var(--color-border)] bg-[var(--color-surface-solid)] px-3 py-2.5 text-[12px] text-[var(--color-text-muted)]">
                {t.auth.demoAccountsEmpty}
              </p>
            )}

            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              {accounts.map((a) => {
                const selected = userId === a.user_id
                return (
                  <button
                    key={a.user_id}
                    type="button"
                    onClick={() => { setUserId(a.user_id); setPassword(a.password); setError(null) }}
                    aria-pressed={selected}
                    className={`focus-ring group rounded-[12px] px-3 py-2.5 text-left transition-all duration-150 ${
                      selected
                        ? 'bg-[var(--color-primary)] text-white'
                        : 'border border-[var(--color-border)] bg-[var(--color-surface-solid)] hover:border-[var(--color-primary)]'
                    }`}
                  >
                    <span className="flex items-center justify-between gap-2">
                      <span className="mono-id text-[12.5px] font-semibold">{a.user_id}</span>
                      <span className={selected ? 'text-white/85' : 'text-[var(--color-primary)]'}>
                        <Icon name={selected ? 'check' : 'user'} size={13} />
                      </span>
                    </span>
                    <span className={`mt-0.5 block text-[10.5px] font-semibold uppercase tracking-wider ${selected ? 'text-white/85' : 'text-[var(--color-primary)]'}`}>
                      {tok(t.tokens.role, a.role)}
                    </span>
                    <span className={`mt-1 block text-[11px] leading-snug ${selected ? 'text-white/80' : 'text-[var(--color-text-muted)]'}`}>
                      {t.auth.roleNote[a.role as keyof typeof t.auth.roleNote] || t.auth.roleNote.DEFAULT}
                    </span>
                  </button>
                )
              })}
            </div>

            <p className="banner-honesty mt-3.5 px-3 py-2.5 text-[11px] leading-relaxed">
              {t.auth.syntheticNotice}
            </p>
          </div>
        </section>

        {/* ── what the console does, kept below the card ─────────────────── */}
        <div className="mt-5 w-full max-w-[900px] px-1">
          <div className="flex flex-wrap items-center justify-center gap-x-2 gap-y-1.5">
            {t.auth.pipeline.map((s, i, arr) => (
              <span key={s} className="flex items-center gap-2">
                <span className="rounded-md border border-[var(--color-border)] bg-[var(--color-surface-solid)] px-2 py-1 text-[11px] font-semibold text-[var(--color-text)]">{s}</span>
                {i < arr.length - 1 && <span className="text-[var(--color-primary)]/45">→</span>}
              </span>
            ))}
          </div>
          <p className="mx-auto mt-3 max-w-[760px] text-center text-[12px] leading-relaxed text-[var(--color-text-muted)]">
            {t.common.principleLines.slice(0, -1).join(' ')}{' '}
            <span className="font-semibold text-[var(--color-primary-deep)]">{t.common.principleLines[t.common.principleLines.length - 1]}</span>
          </p>
          <div className="mt-3 flex flex-wrap items-center justify-center gap-x-4 gap-y-1 text-[10.5px] font-semibold uppercase tracking-[0.16em] text-[var(--color-text-muted)]">
            <span>{t.auth.restrictedFooter}</span>
            <span className="mono-id normal-case tracking-normal">{stamp}</span>
          </div>
        </div>
      </div>
    </div>
  )
}

function ServiceState({ state, onRetry }: { state: 'checking' | 'online' | 'offline'; onRetry: () => void }) {
  const { t } = useI18n()
  if (state === 'offline') {
    return (
      <div className="mt-3.5 flex flex-wrap items-center gap-2 rounded-[12px] border border-[var(--color-danger)] bg-[rgba(196,52,31,0.06)] px-3 py-2">
        <span className="flex h-2 w-2 rounded-full bg-[var(--color-danger)]" />
        <span className="text-[12px] font-semibold text-[var(--color-danger)]">{t.auth.servicesOffline}</span>
        <button onClick={onRetry} className="focus-ring ml-auto rounded-lg border border-[var(--color-danger)] px-2.5 py-1 text-[11.5px] font-bold text-[var(--color-danger)] transition hover:bg-[rgba(196,52,31,0.08)]">
          {t.common.retry}
        </button>
      </div>
    )
  }
  return (
    <div className="mt-3.5 flex items-center gap-2 rounded-[12px] border border-[var(--color-success)] bg-[rgba(30,142,90,0.06)] px-3 py-2">
      <span className={`flex h-2 w-2 rounded-full ${state === 'online' ? 'bg-[var(--color-success)]' : 'bg-[var(--color-warning)]'}`} />
      <span className="text-[12px] font-semibold text-[var(--color-success)]">
        {state === 'online' ? t.auth.servicesOnline : t.auth.servicesChecking}
      </span>
      <span className="ml-auto text-[10.5px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">TLS · JWT</span>
    </div>
  )
}
