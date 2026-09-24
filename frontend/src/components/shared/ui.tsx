import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { useEffect, useState } from 'react'
import { Icon } from './Icon'
import { useI18n } from '../../i18n/LanguageContext'
import { resolveStatus } from '../../i18n'
import type { IconName } from './Icon'
import { api } from '../../services/api'

/* ============================================================================
   CRIMENET AI — SHARED UI KIT
   Every component here reads the design system in src/index.css: no component
   hand-picks a colour. Two surface families, used for different jobs:

     glass   (--color-surface + blur)  top nav, side panel, drawers, modals,
                                       evidence header bar, KPI cards
     solid   (--color-surface-solid)   tables, forms, evidence text, body copy

   Status language is fixed and shared: VERIFIED is a filled success badge,
   CANDIDATE/UNVERIFIED is an outlined warning badge, REJECTED is outlined
   danger with the claim struck through, INSUFFICIENT is dashed muted. A
   candidate must never look as settled as a verified finding.
   ============================================================================ */

/* ---------------------------------------------------------------- surfaces */
export function Card({
  children, className = '', title, subtitle, icon, actions, strong = false, id, solid = false,
}: {
  children?: ReactNode
  className?: string
  title?: string
  subtitle?: string
  icon?: IconName
  actions?: ReactNode
  strong?: boolean
  solid?: boolean
  id?: string
}) {
  return (
    <section id={id} className={`${solid ? 'surface-solid' : strong ? 'glass-strong' : 'glass'} ${className}`}>
      {(title || actions) && (
        <header className="flex flex-wrap items-start justify-between gap-3 border-b border-[var(--color-border)] px-5 py-3.5">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              {icon && <span className="text-[var(--color-primary)]"><Icon name={icon} size={16} /></span>}
              <h2 className="card-title truncate">{title}</h2>
            </div>
            {subtitle && <p className="mt-1 text-[13px] leading-snug text-[var(--color-text-muted)]">{subtitle}</p>}
          </div>
          {actions && <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>}
        </header>
      )}
      <div className={solid ? 'px-5 py-4' : 'px-5 py-4'}>{children}</div>
    </section>
  )
}

/* ---------------------------------------------------------------- buttons */
type BtnProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'neu' | 'ghost' | 'danger' | 'success' | 'outline'
  size?: 'sm' | 'md'
  icon?: IconName
  loading?: boolean
}

export function Button({
  variant = 'neu', size = 'md', icon, loading, children, className = '', disabled, ...rest
}: BtnProps) {
  const base =
    'focus-ring inline-flex items-center justify-center gap-1.5 rounded-[10px] font-semibold transition-all duration-150 disabled:cursor-not-allowed disabled:opacity-55'
  const sizes = size === 'sm' ? 'px-2.5 py-1.5 text-[12px]' : 'px-3.5 py-2 text-[13px]'
  const variants: Record<string, string> = {
    primary:
      'bg-[var(--color-primary)] text-white shadow-[0_8px_18px_-10px_rgba(20,80,196,0.75)] hover:bg-[#0F3FA4] active:translate-y-px',
    outline:
      'bg-[var(--color-surface-solid)] text-[var(--color-primary)] border border-[var(--color-primary)] hover:bg-[var(--color-primary-soft)]',
    neu: 'bg-[var(--color-surface-solid)] text-[var(--color-text)] border border-[var(--color-border)] hover:border-[var(--color-primary)] hover:text-[var(--color-primary)]',
    ghost: 'text-[var(--color-primary)] hover:bg-[var(--color-primary-soft)]',
    danger:
      'bg-[var(--color-danger)] text-white shadow-[0_8px_18px_-10px_rgba(196,52,31,0.7)] hover:bg-[#A62B19] active:translate-y-px',
    success:
      'bg-[var(--color-success)] text-white shadow-[0_8px_18px_-10px_rgba(30,142,90,0.7)] hover:bg-[#176F46] active:translate-y-px',
  }
  return (
    <button className={`${base} ${sizes} ${variants[variant]} ${className}`} disabled={disabled || loading} {...rest}>
      {loading ? <Spinner size={14} /> : icon ? <Icon name={icon} size={size === 'sm' ? 14 : 16} /> : null}
      {children}
    </button>
  )
}

export function Spinner({ size = 16, className = '' }: { size?: number; className?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" className={`animate-spin ${className}`} aria-hidden>
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeOpacity="0.22" strokeWidth="3" fill="none" />
      <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth="3" strokeLinecap="round" fill="none" />
    </svg>
  )
}

/* ---------------------------------------------------------------- badges */
const toneMap: Record<string, string> = {
  blue: 'bg-[var(--color-primary-soft)] text-[var(--color-primary-deep)] ring-[var(--color-primary)]/25',
  navy: 'bg-[rgba(11,47,115,0.06)] text-[var(--color-primary-deep)] ring-[rgba(11,47,115,0.14)]',
  green: 'bg-[var(--color-success)] text-white ring-[var(--color-success)]',
  amber: 'bg-transparent text-[var(--color-warning)] ring-[var(--color-warning)]',
  red: 'bg-transparent text-[var(--color-danger)] ring-[var(--color-danger)]',
  slate: 'bg-transparent text-[var(--color-text-muted)] ring-[var(--color-text-muted)]',
  violet: 'bg-[var(--color-primary-soft)] text-[#5B3FA8] ring-[rgba(91,63,168,0.4)]',
}

export function Badge({
  children, tone = 'blue', className = '', icon, dashed = false, filled = false,
}: {
  children: ReactNode
  tone?: keyof typeof toneMap
  className?: string
  icon?: IconName
  dashed?: boolean
  filled?: boolean
}) {
  const solid = filled || tone === 'green'
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide ring-1 ${
        solid ? `bg-[var(--color-success)] text-white ring-[var(--color-success)]` : toneMap[tone]
      } ${dashed ? '!border !border-dashed' : ''} ${className}`}
      style={dashed && !solid ? { borderStyle: 'dashed' } : undefined}
    >
      {icon && <Icon name={icon} size={12} />}
      {children}
    </span>
  )
}

export function supportTone(level?: string): keyof typeof toneMap {
  switch ((level || '').toUpperCase()) {
    case 'HIGH': return 'green'
    case 'MEDIUM': return 'amber'
    case 'LOW': return 'slate'
    case 'INSUFFICIENT': return 'slate'
    default: return 'slate'
  }
}

export function statusTone(status?: string): keyof typeof toneMap {
  const s = (status || '').toUpperCase()
  if (s.includes('HUMAN_VERIFIED') || s === 'VERIFIED' || s.includes('CORROBORATED ANALYTICAL')) return 'green'
  if (s.includes('REJECT')) return 'red'
  if (s.includes('MISMATCH') || s.includes('CONTRADICT')) return 'red'
  if (s.includes('INSUFFICIENT')) return 'slate'
  if (s.includes('PARTIAL') || s.includes('CANDIDATE') || s.includes('REVIEW') || s.includes('PENDING')) return 'amber'
  if (s.includes('UNVERIFIED') || s.includes('UNCHECKED')) return 'slate'
  return 'blue'
}

/** Which of the four fixed status classes a raw status maps to. */
export type StatusKind = 'verified' | 'candidate' | 'rejected' | 'insufficient' | 'neutral'

export function statusKind(status?: string): StatusKind {
  const s = (status || '').toUpperCase()
  if (s.includes('REJECT')) return 'rejected'
  if (s.includes('INSUFFICIENT')) return 'insufficient'
  if (s.includes('HUMAN_VERIFIED') || s === 'VERIFIED' || s.includes('CORROBORATED ANALYTICAL')) return 'verified'
  if (s.includes('UNVERIFIED') || s.includes('UNCHECKED') || s.includes('CANDIDATE')
      || s.includes('PARTIAL') || s.includes('PENDING') || s.includes('REVIEW')) return 'candidate'
  return 'neutral'
}

const kindClass: Record<StatusKind, string> = {
  verified: 'status-verified',
  candidate: 'status-candidate',
  rejected: 'status-rejected',
  insufficient: 'status-insufficient',
  neutral: 'bg-[var(--color-primary-soft)] text-[var(--color-primary-deep)] border border-[rgba(20,80,196,0.25)]',
}

/**
 * The product's status badge. VERIFIED is the only filled one; a candidate is
 * outlined so it never reads as a confirmed fact; rejected is dashed danger with
 * the claim struck through; insufficient is dashed muted.
 */
export function StatusPill({ status, label, strike = false }: { status?: string; label?: string; strike?: boolean }) {
  const { t } = useI18n()
  const kind = statusKind(status)
  const text = label ?? resolveStatus(t.tokens, status) ?? t.common.unknown
  return (
    <span className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide ${kindClass[kind]}`}>
      {kind === 'verified' && <Icon name="check" size={11} />}
      {kind === 'rejected' && <Icon name="reject" size={11} />}
      {kind === 'insufficient' && <Icon name="info" size={11} />}
      {kind === 'candidate' && <Icon name="clock" size={11} />}
      <span className={kind === 'rejected' && strike ? 'status-rejected-claim' : ''}>{text}</span>
    </span>
  )
}

export function SupportBadge({ level }: { level?: string }) {
  const { t, tok } = useI18n()
  const value = tok(t.tokens.supportLevel, level, t.common.unknown)
  // A HIGH support level backed by evidence is the filled state; everything else stays outlined.
  if ((level || '').toUpperCase() === 'HIGH') {
    return (
      <span className="inline-flex items-center gap-1 rounded-md status-verified px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide">
        <Icon name="check" size={11} /> {value}
      </span>
    )
  }
  return <Badge tone={supportTone(level)} dashed={(level || '').toUpperCase() === 'INSUFFICIENT'}>{value}</Badge>
}

export function StatusBadge({ status }: { status?: string }) {
  return <StatusPill status={status} />
}

export function SourceTrustBadge({ trust, weight }: { trust?: string; weight?: number }) {
  const cat = (trust || 'OFFICER_UPLOAD').toUpperCase()
  const tone: keyof typeof toneMap = cat === 'OFFICER_UPLOAD' ? 'green' : cat === 'BULK_IMPORT' ? 'blue' : 'amber'
  return (
    <Badge tone={tone} icon={cat === 'OFFICER_UPLOAD' ? 'shield' : 'upload'}
           dashed={cat === 'EXTERNAL_SUBMISSION'}>
      {cat.replace(/_/g, ' ')}{typeof weight === 'number' ? ` · w${weight.toFixed(2)}` : ''}
    </Badge>
  )
}

export const entityTone: Record<string, string> = {
  PERSON: '#1450C4', ALIAS: '#4C8FEA', VEHICLE: '#1E8E5A', PHONE: '#5B3FA8',
  ACCOUNT: '#B8791A', LOCATION: '#2FA7DB', ORGANIZATION: '#A03A6B', DEVICE: '#5B6B85',
  EVENT: '#6D4ACA', CASE: '#0B2F73', EVIDENCE: '#5B6B85',
}

export function EntityChip({ type, label, onClick }: { type: string; label: string; onClick?: () => void }) {
  const { t, tok } = useI18n()
  const color = entityTone[type] || '#5B6B85'
  const Tag: any = onClick ? 'button' : 'span'
  return (
    <Tag
      onClick={onClick}
      className={`inline-flex max-w-full items-center gap-1.5 rounded-md border border-[var(--color-border)] bg-[var(--color-surface-solid)] px-2 py-1 text-[12px] font-medium text-[var(--color-text)] ${onClick ? 'focus-ring transition hover:border-[var(--color-primary)]' : ''}`}
    >
      <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: color }} />
      <span className={`truncate ${type === 'PHONE' || type === 'ACCOUNT' || type === 'DEVICE' ? 'mono-id' : ''}`}>{label}</span>
      <span className="shrink-0 text-[10px] font-semibold uppercase tracking-wide text-[var(--color-text-muted)]">{tok(t.tokens.entityType, type)}</span>
    </Tag>
  )
}

/* ---------------------------------------------------------------- states */
export function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`skeleton rounded-lg ${className}`} />
}

/** Real loading skeleton: glass-panel shimmer shaped like the content to come. */
export function LoadingBlock({ label, rows = 3, variant = 'rows' }: { label?: string; rows?: number; variant?: 'rows' | 'cards' | 'table' }) {
  const { t } = useI18n()
  const text = label ?? t.common.runningAnalysis
  return (
    <div className="fade-in space-y-3" role="status" aria-live="polite">
      <div className="flex items-center gap-2 text-[13px] font-medium text-[var(--color-text-muted)]">
        <Spinner size={14} /> {text}
      </div>
      {variant === 'cards' ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: rows }).map((_, i) => (
            <div key={i} className="glass p-4">
              <Skeleton className="h-3 w-24" />
              <Skeleton className="mt-3 h-8 w-16" />
              <Skeleton className="mt-3 h-3 w-32" />
            </div>
          ))}
        </div>
      ) : variant === 'table' ? (
        <div className="surface-solid p-4">
          <Skeleton className="h-4 w-40" />
          {Array.from({ length: rows }).map((_, i) => (
            <Skeleton key={i} className="mt-3 h-9 w-full" />
          ))}
        </div>
      ) : (
        <div className="glass p-4">
          {Array.from({ length: rows }).map((_, i) => (
            <Skeleton key={i} className="mt-2 h-14 w-full first:mt-0" />
          ))}
        </div>
      )}
    </div>
  )
}

export function EmptyState({
  title, message, icon = 'info', action, hint,
}: { title: string; message?: string; icon?: IconName; action?: ReactNode; hint?: string }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-[16px] border border-dashed border-[var(--color-border)] bg-[var(--color-surface-solid)] px-6 py-10 text-center">
      <span className="mb-3 rounded-full bg-[var(--color-primary-soft)] p-2.5 text-[var(--color-primary)]">
        <Icon name={icon} size={20} />
      </span>
      <p className="text-[15px] font-semibold text-[var(--color-primary-deep)]">{title}</p>
      {message && <p className="mt-1.5 max-w-lg text-[13.5px] leading-relaxed text-[var(--color-text-muted)]">{message}</p>}
      {action && <div className="mt-4">{action}</div>}
      {hint && <p className="mt-3 text-[12px] text-[var(--color-text-muted)]">{hint}</p>}
    </div>
  )
}

export function InsufficientEvidence({ message, gap }: { message?: string; gap?: string }) {
  const { t } = useI18n()
  return (
    <div className="rounded-[16px] border border-dashed border-[var(--color-text-muted)] bg-[var(--color-surface-solid)] p-4">
      <div className="flex items-start gap-3">
        <span className="mt-0.5 rounded-lg bg-[var(--color-primary-soft)] p-1.5 text-[var(--color-text-muted)]">
          <Icon name="alert" size={16} />
        </span>
        <div className="min-w-0">
          <p className="text-[13px] font-bold uppercase tracking-wider text-[var(--color-text-muted)]">
            {t.common.insufficientEvidence}
          </p>
          <p className="mt-1 text-[13.5px] leading-relaxed text-[var(--color-text)]">
            {message || t.common.insufficientEvidenceBody}
          </p>
          {gap && (
            <p className="mt-2 text-[12.5px] text-[var(--color-text-muted)]">
              <span className="font-semibold">{t.common.insufficientEvidenceGapLabel}:</span> {gap}
            </p>
          )}
        </div>
      </div>
    </div>
  )
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  const { t } = useI18n()
  return (
    <div className="rounded-[16px] border border-[var(--color-danger)] bg-[var(--color-surface-solid)] p-4">
      <div className="flex items-start gap-3">
        <span className="mt-0.5 rounded-lg bg-[rgba(196,52,31,0.08)] p-1.5 text-[var(--color-danger)]">
          <Icon name="alert" size={16} />
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-[13px] font-bold text-[var(--color-danger)]">{t.common.errorTitle}</p>
          <p className="mt-1 break-words text-[13.5px] text-[var(--color-text)]">{message}</p>
        </div>
        {onRetry && <Button size="sm" icon="refresh" onClick={onRetry}>{t.common.retry}</Button>}
      </div>
    </div>
  )
}

/* ---------------------------------------------------------------- layout bits */
export function PageHeader({
  title, tagline, description, children,
}: { title: string; tagline?: string; description?: string; children?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div className="min-w-0">
        {tagline && (
          <p className="mb-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--color-primary)]">{tagline}</p>
        )}
        <h1 className="page-title">{title}</h1>
        {description && (
          <p className="mt-1.5 max-w-3xl text-[14px] leading-relaxed text-[var(--color-text-muted)]">{description}</p>
        )}
      </div>
      {children && <div className="flex flex-wrap items-center gap-2">{children}</div>}
    </div>
  )
}

/** Section header inside a page: 16px/600 uppercase, muted (spec). */
export function SectionHeader({ children, action }: { children: ReactNode; action?: ReactNode }) {
  return (
    <div className="mb-3 flex items-end justify-between gap-3">
      <h2 className="section-header">{children}</h2>
      {action}
    </div>
  )
}

/** Glass KPI card used on the Dashboard. */
export function KpiCard({
  label, value, hint, icon, tone = 'blue', onClick, loading = false,
}: {
  label: string
  value: ReactNode
  hint?: string
  icon?: IconName
  tone?: keyof typeof toneMap
  onClick?: () => void
  loading?: boolean
}) {
  const Tag: any = onClick ? 'button' : 'div'
  if (loading) {
    return (
      <div className="glass p-4">
        <Skeleton className="h-3 w-24" />
        <Skeleton className="mt-3 h-8 w-14" />
        <Skeleton className="mt-3 h-3 w-28" />
      </div>
    )
  }
  return (
    <Tag
      onClick={onClick}
      className={`glass lift group w-full px-4 py-3.5 text-left ${onClick ? 'focus-ring cursor-pointer' : ''}`}
    >
      <div className="flex items-start justify-between gap-2">
        <p className="section-header !text-[12.5px]">{label}</p>
        {icon && (
          <span className={`rounded-lg p-1.5 ring-1 ${toneMap[tone]}`}>
            <Icon name={icon} size={14} />
          </span>
        )}
      </div>
      <p className="data-num mt-2 text-[28px] font-semibold leading-none text-[var(--color-primary-deep)]">{value}</p>
      {hint && <p className="mt-1.5 text-[12px] leading-snug text-[var(--color-text-muted)]">{hint}</p>}
      {onClick && (
        <span className="absolute bottom-3 right-3 text-[var(--color-primary)] opacity-0 transition group-hover:opacity-100">
          <Icon name="arrowRight" size={15} />
        </span>
      )}
    </Tag>
  )
}

export const StatTile = KpiCard

export function Field({
  label, hint, children, required,
}: { label: string; hint?: string; children: ReactNode; required?: boolean }) {
  return (
    <label className="block">
      <span className="mb-1 flex items-center gap-1 text-[12.5px] font-semibold text-[var(--color-text)]">
        {label} {required && <span className="text-[var(--color-danger)]">*</span>}
      </span>
      {children}
      {hint && <span className="mt-1 block text-[11.5px] text-[var(--color-text-muted)]">{hint}</span>}
    </label>
  )
}

const inputBase =
  'focus-ring w-full rounded-[10px] border border-[var(--color-border)] bg-[var(--color-surface-solid)] px-3 py-2 text-[13.5px] text-[var(--color-text)] placeholder:text-[var(--color-text-muted)]/60 transition focus:border-[var(--color-primary)]'

export function TextInput(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={`${inputBase} ${props.className || ''}`} />
}
export function TextArea(props: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea {...props} className={`${inputBase} min-h-[90px] resize-y ${props.className || ''}`} />
}
export function Select(props: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return <select {...props} className={`${inputBase} pr-8 ${props.className || ''}`} />
}

export function Modal({
  open, onClose, title, subtitle, children, footer, width = 'max-w-2xl',
}: {
  open: boolean
  onClose: () => void
  title: string
  subtitle?: string
  children: ReactNode
  footer?: ReactNode
  width?: string
}) {
  const { t: tModal } = useI18n()
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-[rgba(6,21,50,0.35)] p-0 backdrop-blur-sm sm:items-center sm:p-4" role="dialog" aria-modal="true">
      <div className={`glass fade-in relative flex max-h-[92vh] w-full ${width} flex-col overflow-hidden rounded-t-2xl sm:rounded-[16px]`}>
        <header className="flex items-start justify-between gap-3 border-b border-[var(--color-border)] px-5 py-4">
          <div className="min-w-0">
            <h3 className="truncate text-[16px] font-semibold text-[var(--color-primary-deep)]">{title}</h3>
            {subtitle && <p className="mt-0.5 text-[12.5px] text-[var(--color-text-muted)]">{subtitle}</p>}
          </div>
          <button onClick={onClose} aria-label={tModal.common.close} className="focus-ring rounded-lg p-1.5 text-[var(--color-text-muted)] transition hover:bg-[var(--color-primary-soft)]">
            <Icon name="close" size={18} />
          </button>
        </header>
        <div className="min-h-0 flex-1 overflow-y-auto bg-[var(--color-surface-solid)] px-5 py-4">{children}</div>
        {footer && (
          /* readable, opaque action bar: buttons and labels never sit on blur */
          <footer className="flex flex-wrap justify-end gap-2 border-t border-[var(--color-border)] bg-[var(--color-surface-solid)] px-5 py-3">{footer}</footer>
        )}
      </div>
    </div>
  )
}

export function SignalRow({ signal }: { signal: { signal: string; value?: string; supports?: boolean; present?: boolean; detail?: string } }) {
  const ok = signal.supports ?? signal.present ?? false
  return (
    <li className="flex items-start gap-2 py-1">
      <span className={`mt-0.5 shrink-0 ${ok ? 'text-[var(--color-success)]' : 'text-[var(--color-text-muted)]'}`}>
        <Icon name={ok ? 'check' : 'close'} size={14} />
      </span>
      <span className="min-w-0 text-[13.5px] leading-snug">
        <span className="font-semibold text-[var(--color-text)]">{signal.signal}</span>
        {signal.value ? <span className="text-[var(--color-text)]"> — {signal.value}</span> : null}
        {signal.detail ? <span className="block text-[12px] text-[var(--color-text-muted)]">{signal.detail}</span> : null}
      </span>
    </li>
  )
}

export function KeyValue({ items }: { items: Array<[string, ReactNode]> }) {
  return (
    <dl className="grid grid-cols-1 gap-x-6 gap-y-2.5 sm:grid-cols-2">
      {items.map(([k, v]) => (
        <div key={k} className="min-w-0">
          <dt className="text-[11px] font-semibold uppercase tracking-wide text-[var(--color-text-muted)]">{k}</dt>
          <dd className="mt-0.5 break-words text-[13.5px] font-medium text-[var(--color-text)]">{v ?? '—'}</dd>
        </div>
      ))}
    </dl>
  )
}

export function Hash({ value, chars = 16 }: { value?: string; chars?: number }) {
  if (!value) return <span className="text-[var(--color-text-muted)]">—</span>
  return (
    <span title={value} className="mono-id inline-flex items-center gap-1 rounded bg-[rgba(15,42,89,0.05)] px-1.5 py-0.5 text-[var(--color-primary-deep)]">
      <Icon name="hash" size={11} />
      {value.slice(0, chars)}…
    </span>
  )
}

/* tables: always on a solid surface */
export function ScrollTable({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <div className={`surface-solid overflow-x-auto ${className}`}>
      <table className="w-full min-w-[640px] border-collapse text-left text-[13.5px]">{children}</table>
    </div>
  )
}

export function Th({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <th className={`whitespace-nowrap border-b border-[var(--color-border)] bg-[var(--color-primary-soft)] px-3 py-2.5 text-[11px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)] ${className}`}>
      {children}
    </th>
  )
}

export function Td({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <td className={`border-b border-[var(--color-border)] px-3 py-2.5 align-top text-[var(--color-text)] ${className}`}>{children}</td>
}

export function ClassificationTag({ className = '' }: { className?: string }) {
  const { t } = useI18n()
  return (
    <span className={`banner-honesty inline-flex items-center gap-1 px-2 py-0.5 text-[10.5px] font-bold uppercase tracking-[0.12em] ${className}`}>
      <Icon name="info" size={11} /> {t.common.classificationBanner}
    </span>
  )
}

/** Provenance strip shown above an evidence reading panel (glass header bar). */
export function ProvenanceStrip({ items }: { items: Array<[string, ReactNode]> }) {
  return (
    <div className="glass flex flex-wrap items-center gap-x-6 gap-y-2 px-5 py-3">
      {items.map(([k, v]) => (
        <div key={k} className="min-w-0">
          <p className="text-[10.5px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">{k}</p>
          <div className="mt-0.5 truncate text-[13px] font-medium text-[var(--color-text)]">{v ?? '—'}</div>
        </div>
      ))}
    </div>
  )
}

/**
 * A masked identifier (see app/security/pii.py). The mask is the default view;
 * the full value is fetched only by the audited reveal action and the reveal is
 * recorded against the officer who pressed the button.
 */
export function MaskedValue({
  value, entityId, masked, revealEndpoint,
}: { value: string; entityId?: string; masked?: boolean; revealEndpoint?: string }) {
  const [revealed, setRevealed] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  if (!masked) return <span className="mono-id">{value}</span>
  const endpoint = revealEndpoint || (entityId ? `/api/entities/${entityId}/reveal` : null)
  const reveal = async () => {
    if (!endpoint) return
    setBusy(true); setError(null)
    try {
      const data = await api.get<any>(endpoint)
      setRevealed(data.value)
    } catch (e: any) {
      setError(e?.message || 'reveal failed')
    } finally {
      setBusy(false)
    }
  }
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className="mono-id">{revealed ?? value}</span>
      {revealed ? (
        <span className="text-[10.5px] font-semibold uppercase tracking-wide text-[var(--color-success)]">revealed · audited</span>
      ) : (
        <button
          onClick={reveal}
          disabled={busy}
          title="Reveal the full identifier — this action is written to the audit trail"
          className="focus-ring inline-flex items-center gap-1 rounded border border-[var(--color-border)] px-1.5 py-0.5 text-[10.5px] font-semibold uppercase tracking-wide text-[var(--color-primary)] transition hover:border-[var(--color-primary)]"
        >
          <Icon name="eye" size={11} /> {busy ? '…' : 'reveal'}
        </button>
      )}
      {error && <span className="text-[10.5px] text-[var(--color-danger)]">{error}</span>}
    </span>
  )
}

export function Principle({ compact = false }: { compact?: boolean }) {
  const { t } = useI18n()
  return (
    <div className={`surface-solid ${compact ? 'px-4 py-3' : 'px-5 py-4'}`}>
      <p className="section-header !text-[12.5px] mb-1.5">{t.common.principleTitle}</p>
      <p className={`${compact ? 'text-[12.5px]' : 'text-[13.5px]'} font-medium leading-relaxed text-[var(--color-text)]`}>
        {t.common.principleLines.slice(0, -1).join(' ')}{' '}
        <span className="text-[var(--color-primary)]">{t.common.principleLines[t.common.principleLines.length - 1]}</span>
      </p>
    </div>
  )
}

/** Small helper for pages that want to react to a media query without a library. */
export function useMediaQuery(query: string) {
  const [matches, setMatches] = useState(() => typeof window !== 'undefined' && window.matchMedia(query).matches)
  useEffect(() => {
    const m = window.matchMedia(query)
    const handler = () => setMatches(m.matches)
    handler()
    m.addEventListener('change', handler)
    return () => m.removeEventListener('change', handler)
  }, [query])
  return matches
}
