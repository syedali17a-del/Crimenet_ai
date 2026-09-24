import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, NavLink, useLocation, useNavigate } from 'react-router-dom'
import { Icon } from '../shared/Icon'
import type { IconName } from '../shared/Icon'
import { Badge, Button, ClassificationTag, EmptyState } from '../shared/ui'
import { useApp } from '../../state/AppContext'
import { api } from '../../services/api'
import { useI18n } from '../../i18n/LanguageContext'
import LanguageSwitcher from './LanguageSwitcher'

/* ============================================================================
   APP SHELL
   Top bar and side panel are the only always-on glass surfaces. The side panel
   is fixed and scrolls on its own; the content column scrolls independently of
   it. Dense content (tables, evidence text, forms) lives on solid surfaces.
   ============================================================================ */

type NavKey = keyof ReturnType<typeof useI18n>['t']['nav']['items']
type GroupKey = keyof ReturnType<typeof useI18n>['t']['nav']['groups']
interface NavItem { to: string; key: NavKey; icon: IconName; permission?: string; group: GroupKey }

const NAV: NavItem[] = [
  { to: '/dashboard', key: 'dashboard', icon: 'dashboard', group: 'Command' },
  { to: '/workflow', key: 'workflow', icon: 'branch', group: 'Command' },
  { to: '/cases', key: 'cases', icon: 'cases', permission: 'case:read', group: 'Command' },
  { to: '/evidence', key: 'evidence', icon: 'evidence', permission: 'evidence:read', group: 'Command' },
  { to: '/network', key: 'network', icon: 'network', permission: 'case:read', group: 'Analysis' },
  { to: '/timeline', key: 'timeline', icon: 'timeline', permission: 'case:read', group: 'Analysis' },
  { to: '/map', key: 'map', icon: 'map', permission: 'case:read', group: 'Analysis' },
  { to: '/cross-case', key: 'crossCase', icon: 'crosscase', permission: 'analysis:run', group: 'Analysis' },
  { to: '/entities', key: 'entities', icon: 'entities', permission: 'case:read', group: 'Analysis' },
  { to: '/hypotheses', key: 'hypotheses', icon: 'hypotheses', permission: 'analysis:run', group: 'Reasoning' },
  { to: '/information-gaps', key: 'informationGaps', icon: 'gaps', permission: 'analysis:run', group: 'Reasoning' },
  { to: '/next-best-action', key: 'nextBestAction', icon: 'nextbest', permission: 'analysis:run', group: 'Reasoning' },
  { to: '/audit', key: 'audit', icon: 'audit', permission: 'audit:read', group: 'Assurance' },
  { to: '/security', key: 'security', icon: 'security', permission: 'security:read', group: 'Assurance' },
]

const HEADER_H = 92 // top bar + honesty strip, keeps the fixed nav aligned with content

function Logo({ size = 32 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" aria-hidden>
      <defs>
        <linearGradient id="cn-g" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#2A6FE0" />
          <stop offset="100%" stopColor="#0B2F73" />
        </linearGradient>
      </defs>
      <path d="M24 3 41 10v13c0 10.4-7 17.8-17 22-10-4.2-17-11.6-17-22V10z" fill="url(#cn-g)" />
      <g stroke="#fff" strokeWidth="1.7" fill="none" strokeLinecap="round">
        <circle cx="18" cy="18" r="3" fill="#fff" fillOpacity="0.15" />
        <circle cx="31" cy="22" r="2.6" fill="#fff" fillOpacity="0.15" />
        <circle cx="22" cy="32" r="2.6" fill="#fff" fillOpacity="0.15" />
        <path d="m20.6 19.6 8 1.6M19.4 20.9l1.9 8.6M29.8 24.3l-5.7 6" />
      </g>
    </svg>
  )
}

function GlobalSearch() {
  const { t, tok } = useI18n()
  const [q, setQ] = useState('')
  const [open, setOpen] = useState(false)
  const [results, setResults] = useState<any>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const box = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (box.current && !box.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  useEffect(() => {
    if (q.trim().length < 2) { setResults(null); setError(null); return }
    const timer = setTimeout(async () => {
      setBusy(true); setError(null)
      try {
        const data = await api.get<any>(`/api/search?q=${encodeURIComponent(q.trim())}`)
        setResults(data); setOpen(true)
      } catch (e: any) {
        setResults(null); setError(e?.message || 'search failed'); setOpen(true)
      } finally { setBusy(false) }
    }, 260)
    return () => clearTimeout(timer)
  }, [q])

  const total = results ? (results.total ?? ((results.cases?.length || 0) + (results.entities?.length || 0) + (results.evidence?.length || 0))) : null

  return (
    <div ref={box} className="relative w-full max-w-md">
      <span className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]">
        <Icon name="search" size={15} />
      </span>
      <input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        onFocus={() => results && setOpen(true)}
        placeholder={t.nav.searchPlaceholder}
        aria-label={t.nav.searchAria}
        className="focus-ring w-full rounded-[10px] border border-[var(--color-border)] bg-[var(--color-surface-solid)] py-1.5 pl-8 pr-3 text-[13px] text-[var(--color-text)] placeholder:text-[var(--color-text-muted)]/70 focus:border-[var(--color-primary)]"
      />
      {open && (results || error) && (
        <div className="glass-solid fade-in absolute left-0 right-0 top-[calc(100%+6px)] z-40 max-h-[70vh] overflow-y-auto rounded-[16px] p-2">
          {busy && <p className="px-2 py-1 text-[12px] text-[var(--color-text-muted)]">{t.common.searching}</p>}
          {error && <p className="px-2 py-2 text-[12.5px] text-[var(--color-danger)]">{error}</p>}
          {!busy && !error && total === 0 && (
            <p className="px-2 py-2 text-[12.5px] text-[var(--color-text-muted)]">{t.nav.searchNoMatch(q)}</p>
          )}
          {results?.cases?.length > 0 && (
            <Section title={t.common.cases}>
              {results.cases.map((c: any) => (
                <Row key={c.case_id} onClick={() => { setOpen(false); navigate(`/cases/${c.case_id}`) }}
                  primary={c.case_id} secondary={c.title} icon="cases" />
              ))}
            </Section>
          )}
          {results?.entities?.length > 0 && (
            <Section title={t.common.entities}>
              {results.entities.map((e: any) => (
                <Row key={e.id} onClick={() => { setOpen(false); navigate(`/entities?focus=${e.id}`) }}
                  primary={e.label} secondary={`${tok(t.tokens.entityType, e.entity_type)} · ${e.cases.join(', ') || t.common.none}`} icon="entities" />
              ))}
            </Section>
          )}
          {results?.evidence?.length > 0 && (
            <Section title={t.common.evidence}>
              {results.evidence.map((e: any) => (
                <Row key={e.evidence_id} onClick={() => { setOpen(false); navigate(`/evidence?focus=${e.evidence_id}`) }}
                  primary={e.evidence_id} secondary={`${tok(t.tokens.evidenceType, e.type)} · ${e.source}`} icon="evidence" />
              ))}
            </Section>
          )}
        </div>
      )}
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-1">
      <p className="px-2 pb-1 pt-1.5 text-[10.5px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">{title}</p>
      {children}
    </div>
  )
}

function Row({ primary, secondary, icon, onClick }: { primary: string; secondary: string; icon: IconName; onClick: () => void }) {
  return (
    <button onClick={onClick} className="focus-ring flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left transition hover:bg-[var(--color-primary-soft)]">
      <span className="text-[var(--color-primary)]"><Icon name={icon} size={14} /></span>
      <span className="min-w-0">
        <span className="block truncate text-[13px] font-semibold text-[var(--color-text)]">{primary}</span>
        <span className="block truncate text-[11.5px] text-[var(--color-text-muted)]">{secondary}</span>
      </span>
    </button>
  )
}

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { user, cases, activeCase, setActiveCase, logout, can } = useApp()
  const { t, tok } = useI18n()
  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const [profileOpen, setProfileOpen] = useState(false)
  const [notifOpen, setNotifOpen] = useState(false)
  const [pending, setPending] = useState<any[]>([])
  const location = useLocation()

  useEffect(() => { setMobileOpen(false); setProfileOpen(false); setNotifOpen(false) }, [location.pathname])

  useEffect(() => {
    let alive = true
    api.get<any>(`/api/dashboard${activeCase ? `?case_id=${activeCase}` : ''}`)
      .then((d) => { if (alive) setPending(d.pending_validation || []) })
      .catch(() => undefined)
    return () => { alive = false }
  }, [activeCase, location.pathname])

  const groups = useMemo(() => {
    const visible = NAV.filter((n) => !n.permission || can(n.permission))
    return visible.reduce<Record<string, NavItem[]>>((acc, item) => {
      ;(acc[item.group] = acc[item.group] || []).push(item)
      return acc
    }, {})
  }, [can])

  const navWidth = collapsed ? 76 : 236

  /* ── BUG 1: left-nav scroll affordance ────────────────────────────────────
     The <nav> now owns a definite height (it is a flex item of the fixed
     <aside> with min-h-0), so overflow-y-auto genuinely engages. These two
     refs + the overflow/at-end flags drive (a) the bottom fade that shows the
     list continues below the fold, and (b) scrolling the active item into view
     only when it is actually out of view. */
  const navRef = useRef<HTMLElement | null>(null)
  const activeNavRef = useRef<HTMLAnchorElement | null>(null)
  const [navHint, setNavHint] = useState({ overflowing: false, atEnd: false })

  const syncNavHint = useCallback(() => {
    const el = navRef.current
    if (!el) return
    const overflowing = el.scrollHeight - el.clientHeight > 4
    const atEnd = el.scrollTop + el.clientHeight >= el.scrollHeight - 4
    setNavHint((h) => (h.overflowing === overflowing && h.atEnd === atEnd
      ? h : { overflowing, atEnd }))
  }, [])

  useEffect(() => {
    const el = navRef.current
    if (!el) return
    syncNavHint()
    el.addEventListener('scroll', syncNavHint, { passive: true })
    window.addEventListener('resize', syncNavHint)
    return () => {
      el.removeEventListener('scroll', syncNavHint)
      window.removeEventListener('resize', syncNavHint)
    }
  }, [syncNavHint, collapsed, groups])

  // Scroll the current page's nav item into view — but only when it is not
  // already fully visible, so normal navigation never yanks the sidebar.
  // Deltas are computed from bounding rects and applied to el.scrollTop, which
  // affects only the nav's own scrollport (scrollIntoView can also move an
  // ancestor/document scroll position).
  useEffect(() => {
    const el = navRef.current
    const item = activeNavRef.current
    if (!el || !item) return
    const pad = 12
    const ir = item.getBoundingClientRect()
    const cr = el.getBoundingClientRect()
    if (ir.bottom > cr.bottom - pad) el.scrollTop += (ir.bottom - cr.bottom) + pad
    else if (ir.top < cr.top + pad) el.scrollTop -= (cr.top - ir.top) + pad
    syncNavHint()
  }, [location.pathname, collapsed, syncNavHint])

  const sidebar = (
    <nav
      ref={navRef}
      aria-label={t.nav.openNavigation}
      className="flex min-h-0 flex-1 flex-col gap-5 overflow-y-auto overscroll-contain px-3 py-4"
    >
      {Object.entries(groups).map(([group, items]) => (
        <div key={group}>
          {!collapsed && (
            <p className="px-2.5 pb-1.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-[var(--color-text-muted)]">
              {t.nav.groups[group as GroupKey]}
            </p>
          )}
          <ul className="space-y-1">
            {items.map((item) => (
              <li key={item.to}>
                <NavLink
                  to={item.to}
                  title={t.nav.items[item.key]}
                  ref={location.pathname === item.to || location.pathname.startsWith(`${item.to}/`)
                    ? activeNavRef : undefined}
                  className={({ isActive }) =>
                    `focus-ring group flex items-center gap-2.5 rounded-[10px] px-2.5 py-2 text-[13px] font-medium transition-all duration-150 ${
                      isActive
                        ? 'bg-[var(--color-primary)] text-white shadow-[0_10px_22px_-14px_rgba(20,80,196,0.85)]'
                        : 'text-[var(--color-text)] hover:bg-[var(--color-primary-soft)] hover:text-[var(--color-primary-deep)]'
                    }`
                  }
                >
                  <Icon name={item.icon} size={17} />
                  {!collapsed && <span className="truncate">{t.nav.items[item.key]}</span>}
                </NavLink>
              </li>
            ))}
          </ul>
        </div>
      ))}
      <div className="mt-auto space-y-2">
        {!collapsed && (
          <div className="surface-solid px-3 py-2.5">
            <p className="text-[10.5px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">
              {t.nav.workflowCardTitle}
            </p>
            <p className="mt-1 text-[11.5px] leading-relaxed text-[var(--color-text)]">{t.common.tagline}</p>
          </div>
        )}
        <button
          onClick={() => setCollapsed((c) => !c)}
          className="focus-ring hidden w-full items-center justify-center gap-2 rounded-[10px] py-2 text-[12px] font-semibold text-[var(--color-text-muted)] transition hover:bg-[var(--color-primary-soft)] lg:flex"
        >
          <Icon name="chevron" size={14} className={collapsed ? '' : 'rotate-180'} />
          {!collapsed && t.nav.collapseSidebar}
        </button>
      </div>
    </nav>
  )

  return (
    <div className="min-h-screen w-full">
      {/* ── glass top bar ─────────────────────────────────────────────────── */}
      <header className="glass fixed inset-x-0 top-0 z-40 rounded-none border-x-0 border-t-0">
        <div className="flex items-center gap-2 px-3 py-2.5 sm:gap-3 sm:px-4">
          <button
            className="focus-ring rounded-lg p-1.5 text-[var(--color-text)] transition hover:bg-[var(--color-primary-soft)] lg:hidden"
            onClick={() => setMobileOpen(true)}
            aria-label={t.nav.openNavigation}
          >
            <Icon name="menu" size={20} />
          </button>
          <Link to="/dashboard" className="focus-ring flex shrink-0 items-center gap-2 rounded-lg">
            <Logo size={30} />
            <span className="hidden sm:block">
              <span className="brand-wordmark block text-[15px] font-extrabold leading-none tracking-tight text-[var(--color-primary-deep)]">
                CRIMENET <span className="text-[var(--color-primary)]">AI</span>
              </span>
              <span className="block text-[10px] font-semibold uppercase tracking-[0.12em] text-[var(--color-text-muted)]">
                {t.common.tagline}
              </span>
            </span>
          </Link>

          <div className="ml-1 hidden md:block">
            <select
              value={activeCase || ''}
              onChange={(e) => setActiveCase(e.target.value || null)}
              aria-label={t.nav.activeCaseAria}
              className="focus-ring rounded-[10px] border border-[var(--color-border)] bg-[var(--color-surface-solid)] px-2.5 py-1.5 text-[12.5px] font-semibold text-[var(--color-text)]"
            >
              <option value="">{t.nav.allAuthorizedCases}</option>
              {cases.map((c) => (
                <option key={c.case_id} value={c.case_id}>{c.case_id} — {c.title}</option>
              ))}
            </select>
          </div>

          <div className="ml-auto flex flex-1 items-center justify-end gap-2">
            <div className="hidden flex-1 justify-end sm:flex"><GlobalSearch /></div>

            <LanguageSwitcher />

            <div className="relative">
              <button
                onClick={() => { setNotifOpen((o) => !o); setProfileOpen(false) }}
                aria-label={t.nav.notifications}
                className="focus-ring relative rounded-lg p-1.5 text-[var(--color-text)] transition hover:bg-[var(--color-primary-soft)]"
              >
                <Icon name="bell" size={18} />
                {pending.length > 0 && (
                  <span className="data-num absolute right-0.5 top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-[var(--color-primary)] px-1 text-[9.5px] font-bold text-white">
                    {pending.length}
                  </span>
                )}
              </button>
              {notifOpen && (
                <div className="glass-solid absolute right-0 top-[calc(100%+8px)] z-50 w-[320px] p-3">
                  <p className="section-header !text-[12.5px] mb-2">{t.nav.pendingValidation}</p>
                  {pending.length === 0 ? (
                    <EmptyState title={t.nav.pendingValidationEmpty} icon="check" />
                  ) : (
                    <ul className="space-y-1.5">
                      {pending.slice(0, 5).map((p) => (
                        <li key={p.relationship_id} className="surface-solid px-2.5 py-2">
                          <p className="text-[12.5px] font-semibold text-[var(--color-text)]">
                            {p.source_label} → {p.target_label}
                          </p>
                          <p className="text-[11.5px] text-[var(--color-text-muted)]">
                            {tok(t.tokens.relationshipType, p.relationship_type)} · {p.case_id} · {tok(t.tokens.supportLevel, p.support_level)}
                          </p>
                        </li>
                      ))}
                    </ul>
                  )}
                  <Link to="/network" className="focus-ring mt-2 block rounded text-[12px] font-semibold text-[var(--color-primary)] hover:underline">
                    {t.nav.reviewInNetwork}
                  </Link>
                </div>
              )}
            </div>

            <div className="relative">
              <button
                onClick={() => { setProfileOpen((o) => !o); setNotifOpen(false) }}
                className="focus-ring flex items-center gap-2 rounded-lg px-1.5 py-1 transition hover:bg-[var(--color-primary-soft)]"
              >
                <span className="flex h-7 w-7 items-center justify-center rounded-full bg-[var(--color-primary)] text-[11px] font-bold text-white">
                  {user?.display_name?.split(' ').map((s) => s[0]).slice(0, 2).join('')}
                </span>
                <span className="hidden text-left lg:block">
                  <span className="block text-[12.5px] font-semibold leading-tight text-[var(--color-text)]">{user?.display_name}</span>
                  <span className="block text-[10.5px] font-semibold uppercase tracking-wide text-[var(--color-primary)]">{tok(t.tokens.role, user?.role)}</span>
                </span>
              </button>
              {profileOpen && (
                <div className="glass-solid absolute right-0 top-[calc(100%+8px)] z-50 w-[280px] p-3">
                  <p className="text-[13px] font-bold text-[var(--color-text)]">{user?.display_name}</p>
                  <p className="text-[11.5px] text-[var(--color-text-muted)]">{user?.badge} · {user?.unit}</p>
                  <div className="my-2 flex flex-wrap gap-1">
                    <Badge tone="blue">{tok(t.tokens.role, user?.role)}</Badge>
                    <Badge tone="slate">{t.common.permissionsCount(user?.permissions.length || 0)}</Badge>
                  </div>
                  <p className="mb-2 text-[11.5px] text-[var(--color-text-muted)]">
                    {t.nav.caseAccess}: {user?.case_access.includes('*') ? t.nav.allCases : user?.case_access.join(', ') || t.common.none}
                  </p>
                  <div className="flex gap-2">
                    <Link to="/security" className="flex-1">
                      <Button size="sm" icon="shield" className="w-full">{t.nav.items.security}</Button>
                    </Link>
                    <Button size="sm" variant="ghost" icon="logout" onClick={logout}>{t.common.signOut}</Button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* honesty strip: classification + product subtitle + case context */}
        <div className="flex items-center justify-between gap-2 border-t border-[var(--color-border)] bg-[var(--color-surface-solid)] px-3 py-1.5 sm:px-4">
          <ClassificationTag />
          <p className="hidden truncate text-[11px] text-[var(--color-text-muted)] md:block">{t.common.productSubtitle}</p>
          <p className="truncate text-[11px] font-semibold text-[var(--color-text-muted)]">
            {activeCase ? t.nav.caseContext(activeCase) : t.nav.contextAllCases}
          </p>
        </div>
      </header>

      {/* ── fixed glass side panel, scrolls on its own ────────────────────── */}
      <aside
        style={{ width: navWidth, top: HEADER_H }}
        className="glass fixed bottom-0 left-0 z-30 hidden shrink-0 flex-col overflow-hidden rounded-none border-y-0 border-l-0 transition-[width] duration-200 lg:flex"
      >
        {sidebar}
        {/* BUG 1: bottom fade — visible only while there is more list below… */}
        {navHint.overflowing && !navHint.atEnd && (
          <div
            aria-hidden
            className="pointer-events-none absolute inset-x-0 bottom-0 h-10"
            style={{ background: 'linear-gradient(to bottom, rgba(255,255,255,0) 0%, var(--color-surface) 62%, var(--color-surface) 100%)' }}
          />
        )}
      </aside>

      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div className="absolute inset-0 bg-[rgba(6,21,50,0.4)] backdrop-blur-sm" onClick={() => setMobileOpen(false)} />
          <div className="glass absolute left-0 top-0 h-full w-[260px] overflow-y-auto rounded-none">
            <div className="sticky top-0 flex items-center justify-between border-b border-[var(--color-border)] px-3 py-3">
              <div className="flex items-center gap-2">
                <Logo size={26} />
                <span className="brand-wordmark text-[14px] font-extrabold text-[var(--color-primary-deep)]">CRIMENET AI</span>
              </div>
              <button onClick={() => setMobileOpen(false)} aria-label={t.common.close} className="focus-ring rounded-lg p-1.5">
                <Icon name="close" size={18} />
              </button>
            </div>
            {sidebar}
          </div>
        </div>
      )}

      {/* ── content column: scrolls independently of the nav ──────────────── */}
      <main className="min-w-0 transition-[padding] duration-200 lg:pl-[var(--nav-w)]" style={{ ['--nav-w' as any]: `${navWidth}px`, paddingTop: HEADER_H }}>
        {mobileOpen && null}
        <div className="mx-auto w-full max-w-[1400px] px-4 py-6 sm:px-6">
          <div className="mb-4 sm:hidden"><GlobalSearch /></div>
          <div className="page-enter">{children}</div>
        </div>
      </main>
    </div>
  )
}
