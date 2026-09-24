# Four UI bugs — fixes, evidence and verification

Each bug was a real defect with a specific root cause. Below: the root cause, the exact change, and
the complete updated component as evidence (no screenshots available in this environment).
`scripts/bugfix_verify.sh` asserts all of it from the shipped source and the built CSS bundle —
**30 checks, 30 pass** — and `npm run build` exits 0.

---

## BUG 1 — left nav clipped with no scroll affordance

### Root cause (box model)

```
<aside style="top: 92px" class="glass fixed bottom-0 left-0 ...">   ← fixed, top+bottom set
  <nav class="... min-h-full overflow-y-auto ...">                    ← min-height: 100%
```

1. The `<aside>` is `position: fixed` with both `top: 92px` and `bottom: 0`, so its used height is
   definite: `100vh − 92px`. At a 1080px *viewport* that is 988px; on a 1080p *screen* the viewport
   is nearer 800–900px, so the panel is ~710–810px tall, and the taller Indic line boxes
   (`html.lang-ta body { line-height: 1.65 }`) push the 14 nav items + 4 group labels + workflow card
   past that.
2. The `<nav>` had `min-height: 100%` and **auto** height. A minimum can only make a box taller;
   once its content exceeded the `<aside>`'s height, the nav simply *grew taller than its parent*
   instead of scrolling.
3. The `<aside>` had no `overflow` declaration, i.e. `visible`, so the nav painted past the panel's
   bottom edge — and since that edge is the viewport edge (`bottom: 0`), the overflow landed off
   screen. `overflow-y: auto` on the nav could never fire, because a scroll container whose own box
   is as tall as its content has nothing to scroll.

Net effect: the ASSURANCE group (Audit, Security) was unreachable and invisible, with no scrollbar to
hint at it. The height chain was the actual problem, exactly as suspected.

### Fix — three parts

**(a) Make the height chain definite** so `overflow-y-auto` genuinely engages:

```diff
- <aside ... className="glass fixed bottom-0 left-0 z-30 hidden shrink-0 rounded-none border-y-0 border-l-0 transition-[width] duration-200 lg:block">
+ <aside ... className="glass fixed bottom-0 left-0 z-30 hidden shrink-0 flex-col overflow-hidden rounded-none border-y-0 border-l-0 transition-[width] duration-200 lg:flex">

- <nav className="flex min-h-full flex-col gap-5 overflow-y-auto px-3 py-4">
+ <nav ref={navRef} className="flex min-h-0 flex-1 flex-col gap-5 overflow-y-auto overscroll-contain px-3 py-4">
```

The aside is now a flex column that clips its child; the nav is a flex item with `min-height: 0`
(defeating the flex item's automatic `min-height: auto` floor) and `flex-1`, so it receives a definite
height equal to the panel. Content taller than that now scrolls. `overscroll-contain` keeps that
scroll from chaining to the page. `display: block → flex` and `overflow: visible → hidden` are the two
changes that were actually blocking the scrollbar.

**(b) A bottom fade** so the continuation is visible without hunting for a scrollbar. It renders only
while the list actually overflows *and* is not already scrolled to the end, and it is
`pointer-events-none`, so it never intercepts a click.

**(c) Scroll the active item into view** on mount and on route change, guarded and contained:

```tsx
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
```

Note on the mechanism: I used rect deltas written to `el.scrollTop` rather than
`element.scrollIntoView({ block: 'nearest' })`. `scrollIntoView` bubbles to *ancestor* scrollports,
so opening `/audit` could have nudged the document scroll as a side effect; writing the container's
own `scrollTop` gives the same `block: 'nearest'` semantics with a guarantee that nothing outside the
nav moves. The guard means an item already on screen is never re-scrolled — no yanking on re-render.

### Why Audit now visibly reads as active

`NavLink` forwards a ref (confirmed: react-router 7.18.3 wraps it in `React.forwardRef`), so the
active item is directly addressable. On landing at `/audit` the effect scrolls it into the panel's
view with 12px of breathing room, AND — because the nav is no longer at its end — the bottom fade
stays visible, so the position is legible two ways: the highlight is on screen, and the fade shows
there is more list below.

### Complete updated component

```tsx
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
```

---

## BUG 2 — popovers let the page show through

### Root cause

`.glass-strong` was byte-identical to `.glass`: `background: rgba(255,255,255,0.65)` plus
`backdrop-filter: blur(16px)`. Blur redistributes luminance, it does not remove it, so 35 % of what
is behind the panel survives — and what is behind the profile menu is the **honesty strip**, an
*opaque white* bar whose muted `Context: all authorized cases` label sits in normal flow exactly
where the menu opens. That label ghosted through the menu and crossed the Sign Out button.

### Fix — a real surface for text-bearing overlays

```css
  .glass {
    background: var(--color-surface);
    backdrop-filter: blur(16px) saturate(140%);
    -webkit-backdrop-filter: blur(16px) saturate(140%);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-panel);
    box-shadow: var(--shadow-glass);
  }
  .glass-strong {
    background: var(--color-surface);
    backdrop-filter: blur(16px) saturate(140%);
    -webkit-backdrop-filter: blur(16px) saturate(140%);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-panel);
    box-shadow: var(--shadow-glass);
  }
  /* BUG 2 — solid glass for TEXT-BEARING OVERLAYS (menus, popovers, dropdowns).
     Blur alone does not obscure small high-contrast text sitting directly behind
     the panel: the profile menu opens over the opaque honesty strip, whose muted
     label ghosted through a 65%-alpha panel and crossed the Sign Out button.
     Overlay surfaces the user must read or click are therefore effectively
     opaque; blur stays on large surfaces that carry no small text. */
  .glass-solid {
    background: rgba(255, 255, 255, 0.97);
    backdrop-filter: blur(20px) saturate(120%);
    -webkit-backdrop-filter: blur(20px) saturate(120%);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-panel);
    box-shadow: 0 18px 44px -22px rgba(15, 42, 89, 0.38), 0 2px 6px rgba(15, 42, 89, 0.06);
  }
```

`.glass-solid` is effectively opaque (`#fffffff7` in the built CSS — 247/255 ≈ 0.97), keeps a light
blur for the edges of the panel over varied content, and uses a *tighter* shadow so it reads as a
floating layer rather than a card.

Switched to it — every absolute-positioned menu in the shell:

| overlay | before | after |
| --- | --- | --- |
| global search results (`AppLayout.tsx`) | `glass` | `glass-solid` |
| notifications (`AppLayout.tsx`) | `glass-strong` | `glass-solid` |
| profile menu / Sign Out (`AppLayout.tsx`) | `glass-strong` | `glass-solid` |
| language listbox (`LanguageSwitcher.tsx`) | `glass-strong` | `glass-solid` |

`glass-strong` is retained for surfaces that carry no small interactive text (it is still used by
`Card strong`). Modals were left alone deliberately: `Modal` already renders an opaque scrim
(`bg-[rgba(6,21,50,0.35)] backdrop-blur-sm`) behind its panel, so nothing legible sits directly
behind its text — changing them would be redesign beyond the reported defect.

The complete `AppLayout.tsx` above contains all three menus; the switcher's listbox is:

```tsx
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
```

---

## BUG 3 — the login screen's only control had no label

### Root cause

`Login.tsx` passed `compact`, and `LanguageSwitcher` renders its name span only when
`!compact` — leaving a bare globe and chevron on the first screen a judge sees.

### Fix

```diff
  {/* language stays switchable on the login screen itself */}
- <LanguageSwitcher compact />
+ {/* BUG 3: no `compact` here — an icon-only globe gave the first screen's
+     only control no readable label. The full control shows the language name. */}
+ <LanguageSwitcher />
```

There was no real space constraint to preserve: the login top bar is a `justify-between` flex row
inside a 520px column, the classification banner beside it is `hidden` below `sm`, and the labelled
control is only ~130px wide (globe 15px + name capped at 92px + chevron). The container is
`flex-wrap`-free but has room at every breakpoint, and the label truncates rather than overflowing
(`max-w-[92px] truncate`) in the longest endonym.

### Complete updated Login page

```tsx
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
```

---

## BUG 4 — checkbox label colliding with the end-date field

### Root cause

The filter grid was `grid-cols-1 md:grid-cols-2 xl:grid-cols-4` holding **four** children, one of
which was itself a flex row containing *both* date inputs. At `md` the columns were
`[search | case]` then `[both dates | checkbox label]`, so the checkbox label sat in the narrow cell
directly beside a cell with two dates crammed into it — the end-date calendar icon and the wrapping
label text occupied the same horizontal band.

### Fix — restructure, no restyling

1. Each of the four fields now owns a grid cell (the nested date `<div>` is gone), so the grid is
   genuinely the 4-field grid the layout assumed: search · case · from · to.
2. The `verifiedOnly` checkbox moved into its **own full-width row below** the grid — a separate
   `<div>` outside the grid container, so it cannot compete for column space at any breakpoint.

```diff
  <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
    <TextInput ... search ... />
    <Select ... case ... />
-   <div className="flex items-center gap-2">
-     <TextInput type="date" ... dateFrom ... />
-     <TextInput type="date" ... dateTo ... />
-   </div>
-   <label className="flex items-center gap-2 ...">   ← inside the grid
+   <TextInput type="date" ... dateFrom ... aria-label={t.analysis.tl.startDate} />
+   <TextInput type="date" ... dateTo ...   aria-label={t.analysis.tl.endDate} />
  </div>
+
+ <div className="mt-3">
+   <label className="flex w-fit items-center gap-2 text-[12.5px] font-semibold text-[var(--color-text)]">
+     <input type="checkbox" ... verifiedOnly ... />
+     {t.analysis.net.verifiedOnly}
+   </label>
+ </div>
```

`w-fit` keeps the label at its natural width so it cannot stretch into an adjacent column, and the two
date inputs gained the `aria-label`s they lacked (they were unlabelled before this pass).

### Complete updated page

```tsx
import { useMemo, useRef, useState } from 'react'
import type { Core } from 'cytoscape'
import { useApp } from '../state/AppContext'
import { useFetch } from '../hooks/useFetch'
import { api, ApiError } from '../services/api'
import NetworkGraph, { DEFAULT_FILTERS, filterPayload } from '../components/graph/NetworkGraph'
import EntityPanel, { RelationshipPanel } from '../components/graph/EntityPanel'
import type { GraphFilters } from '../components/graph/NetworkGraph'
import type { GraphPayload } from '../types'
import { Icon } from '../components/shared/Icon'
import {
  Button, Card, EmptyState, ErrorState, InsufficientEvidence, LoadingBlock, PageHeader,
  SectionHeader, Select, TextInput,
} from '../components/shared/ui'
import { useI18n } from '../i18n/LanguageContext'

/* ============================================================================
   NETWORK INTELLIGENCE
   The graph canvas is drawn on a SOLID surface: a working chart must not sit on
   a blurred panel. Glass is used only where the spec allows it here — the filter
   control panel and the inspector drawer that slides over the canvas.
   ============================================================================ */

const ENTITY_TYPES = ['PERSON', 'ALIAS', 'VEHICLE', 'PHONE', 'ACCOUNT', 'LOCATION', 'ORGANIZATION', 'DEVICE', 'CASE']
const REL_TYPES = ['ASSOCIATED_WITH', 'USED', 'LOCATED_AT', 'CONNECTED_TO', 'PART_OF', 'MENTIONED_IN', 'TRANSACTED_WITH', 'OBSERVED_AT', 'RELATED_TO']
const SUPPORTS = ['HIGH', 'MEDIUM', 'LOW']

export default function NetworkIntelligence() {
  const { t } = useI18n()
  const { activeCase, cases, notify, can } = useApp()
  const cyRef = useRef<Core | null>(null)
  const [filters, setFilters] = useState<GraphFilters>({ ...DEFAULT_FILTERS, caseId: activeCase })
  const [selectedNode, setSelectedNode] = useState<string | null>(null)
  const [selectedEdge, setSelectedEdge] = useState<string | null>(null)
  const [showCommunities, setShowCommunities] = useState(false)
  const [path, setPath] = useState<{ from: string; to: string }>({ from: '', to: '' })
  const [pathNodes, setPathNodes] = useState<string[]>([])
  const [pathInfo, setPathInfo] = useState<any>(null)
  const [analysis, setAnalysis] = useState<any>(null)
  const [analysing, setAnalysing] = useState(false)

  const graph = useFetch<GraphPayload>(`/api/graph${activeCase ? `?case_id=${activeCase}` : ''}`, [activeCase])
  const filtered = useMemo(() => filterPayload(graph.data, filters), [graph.data, filters])

  const communities = useMemo(() => {
    const map: Record<string, number> = {}
    ;(analysis?.communities || []).forEach((c: any) => c.members.forEach((m: any) => { map[m.id] = c.community_id }))
    return map
  }, [analysis])

  /** A2 — the per-node structural explanation produced by the backend, indexed by node id. */
  const explanations = useMemo(() => {
    const map: Record<string, { degree?: string; betweenness?: string; score?: string }> = {}
    ;(analysis?.degree_centrality || []).forEach((row: any) => {
      map[row.entity_id] = { ...(map[row.entity_id] || {}), degree: row.interpretation, score: row.score }
    })
    ;(analysis?.betweenness_centrality || []).forEach((row: any) => {
      map[row.entity_id] = { ...(map[row.entity_id] || {}), betweenness: row.interpretation, score: row.score }
    })
    return map
  }, [analysis])

  const nodeOptions = useMemo(
    () => (graph.data?.nodes || []).map((n) => ({ id: n.data.id, label: `${n.data.label} (${n.data.entity_type})` })),
    [graph.data],
  )

  async function runAnalysis() {
    setAnalysing(true)
    try {
      const res = await api.post<any>('/api/analysis/network', { case_ids: activeCase ? [activeCase] : [] })
      setAnalysis(res)
      notify(res.sufficient ? 'success' : 'info', 'Network analysis complete',
        res.sufficient ? `${res.nodes} nodes · ${res.edges} edges · ${res.communities.length} clusters (${res.engine})` : res.message)
    } catch (err) {
      notify('error', 'Network analysis failed', err instanceof ApiError ? err.message : undefined)
    } finally { setAnalysing(false) }
  }

  async function runPath() {
    if (!path.from || !path.to) { notify('info', 'Select both endpoints for the path analysis'); return }
    try {
      const res = await api.post<any>('/api/analysis/shortest-path', {
        source: path.from, target: path.to, case_ids: activeCase ? [activeCase] : [],
      })
      setPathInfo(res)
      if (res.found) {
        setPathNodes(res.path_ids)
        notify('success', `Path found (${res.length} hop(s))`, res.nodes.map((n: any) => n.label).join(' → '))
      } else {
        setPathNodes([])
        notify('info', 'No evidence-backed path', res.message)
      }
    } catch (err) {
      notify('error', 'Path analysis failed', err instanceof ApiError ? err.message : undefined)
    }
  }

  function toggle(list: string[], value: string): string[] {
    return list.includes(value) ? list.filter((v) => v !== value) : [...list, value]
  }

  return (
    <>
      <PageHeader
        tagline={t.pages.network.tagline}
        title={t.pages.network.title}
        description={t.pages.network.description}
      >
        <Button icon="refresh" onClick={graph.reload}>{t.analysis.net.reload}</Button>
        {can('analysis:run') && (
          <Button variant="primary" icon="spark" loading={analysing} onClick={runAnalysis}>{t.analysis.net.runAnalysis}</Button>
        )}
      </PageHeader>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-[1fr_380px]">
        <div className="space-y-5">
          {/* ── filter / path control panel (glass, per spec) ─────────────── */}
          <Card
            title={t.analysis.net.controls}
            icon="filter"
            actions={
              <>
                <Button size="sm" icon="fit" onClick={() => cyRef.current?.fit(undefined, 45)}>{t.analysis.net.fit}</Button>
                <Button size="sm" icon="reset" onClick={() => {
                  setFilters({ ...DEFAULT_FILTERS, caseId: activeCase }); setPathNodes([]); setPathInfo(null)
                  setSelectedEdge(null); setSelectedNode(null)
                  cyRef.current?.layout({ name: 'cose', animate: false, padding: 40 } as any).run()
                }}>{t.analysis.net.reset}</Button>
              </>
            }
          >
            {/* BUG 4: the four fields own one cell each, so the two date inputs are no
                longer squeezed into a single column beside the checkbox label. */}
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
              <TextInput placeholder={t.analysis.net.searchEntity} value={filters.search}
                onChange={(e) => setFilters({ ...filters, search: e.target.value })} />
              <Select value={filters.caseId || ''} onChange={(e) => setFilters({ ...filters, caseId: e.target.value || null })}>
                <option value="">{t.analysis.net.allAuthorizedCases}</option>
                {cases.map((c) => <option key={c.case_id} value={c.case_id}>{c.case_id}</option>)}
              </Select>
              <TextInput type="date" value={filters.dateFrom || ''} aria-label={t.analysis.tl.startDate}
                onChange={(e) => setFilters({ ...filters, dateFrom: e.target.value })} />
              <TextInput type="date" value={filters.dateTo || ''} aria-label={t.analysis.tl.endDate}
                onChange={(e) => setFilters({ ...filters, dateTo: e.target.value })} />
            </div>

            {/* BUG 4: structurally independent of the field grid above — the checkbox
                can never compete for column space with the date inputs at any breakpoint. */}
            <div className="mt-3">
              <label className="flex w-fit items-center gap-2 text-[12.5px] font-semibold text-[var(--color-text)]">
                <input type="checkbox" checked={filters.verifiedOnly} className="h-4 w-4 accent-[var(--color-primary)]"
                  onChange={(e) => setFilters({ ...filters, verifiedOnly: e.target.checked })} />
                {t.analysis.net.verifiedOnly}
              </label>
            </div>

            <div className="mt-4 space-y-2.5">
              <ChipRow label={t.analysis.net.entityType} kind="entityType" values={ENTITY_TYPES} selected={filters.entityTypes}
                onToggle={(v) => setFilters({ ...filters, entityTypes: toggle(filters.entityTypes, v) })} />
              <ChipRow label={t.analysis.net.relationship} kind="relationshipType" values={REL_TYPES} selected={filters.relationshipTypes}
                onToggle={(v) => setFilters({ ...filters, relationshipTypes: toggle(filters.relationshipTypes, v) })} />
              <ChipRow label={t.analysis.net.support} kind="supportLevel" values={SUPPORTS} selected={filters.supportLevels}
                onToggle={(v) => setFilters({ ...filters, supportLevels: toggle(filters.supportLevels, v) })} />
            </div>

            <div className="mt-4 grid grid-cols-1 gap-2 border-t border-[var(--color-border)] pt-4 md:grid-cols-[1fr_1fr_auto_auto]">
              <Select value={path.from} onChange={(e) => setPath({ ...path, from: e.target.value })}>
                <option value="">{t.analysis.net.pathFrom}</option>
                {nodeOptions.map((n) => <option key={n.id} value={n.id}>{n.label}</option>)}
              </Select>
              <Select value={path.to} onChange={(e) => setPath({ ...path, to: e.target.value })}>
                <option value="">{t.analysis.net.pathTo}</option>
                {nodeOptions.map((n) => <option key={n.id} value={n.id}>{n.label}</option>)}
              </Select>
              <Button size="sm" icon="branch" onClick={runPath}>{t.analysis.net.highlightPath}</Button>
              <Button size="sm" icon="eye" variant={showCommunities ? 'primary' : 'neu'}
                onClick={() => { if (!analysis) runAnalysis(); setShowCommunities((s) => !s) }}>
                {t.analysis.net.communities}
              </Button>
            </div>

            {pathInfo && (
              <div className={`mt-4 rounded-[12px] border px-3.5 py-2.5 text-[12.5px] ${
                pathInfo.found
                  ? 'border-[var(--color-primary)] bg-[var(--color-primary-soft)] text-[var(--color-text)]'
                  : 'border-dashed border-[var(--color-text-muted)] bg-[var(--color-surface-solid)] text-[var(--color-text)]'
              }`}>
                {pathInfo.found ? (
                  <>
                    <p className="font-semibold text-[var(--color-primary-deep)]">{pathInfo.nodes.map((n: any) => n.label).join('  →  ')}</p>
                    <p className="mt-1 text-[11.5px] text-[var(--color-text-muted)]">{pathInfo.interpretation}</p>
                  </>
                ) : <p>{pathInfo.message}</p>}
              </div>
            )}
          </Card>

          {/* ── graph canvas: SOLID surface ──────────────────────────────── */}
          <section className="surface-solid">
            <header className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--color-border)] px-5 py-3.5">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-[var(--color-primary)]"><Icon name="network" size={16} /></span>
                  <h2 className="section-header !text-[13px]">{t.analysis.net.graphTitle}</h2>
                </div>
                {filtered && (
                  <p className="mt-1 text-[12.5px] text-[var(--color-text-muted)]">
                    {t.analysis.net.graphSubtitle(filtered.counts.nodes, filtered.counts.edges)}
                  </p>
                )}
              </div>
              <Legend />
            </header>
            <div className="p-5">
              {graph.loading && <LoadingBlock label={t.analysis.net.reconstructing} rows={3} />}
              {graph.error && <ErrorState message={graph.error} onRetry={graph.reload} />}
              {graph.data && !graph.data.sufficient && <InsufficientEvidence message={graph.data.message} />}
              {filtered && filtered.counts.nodes > 0 && (
                <NetworkGraph
                  payload={filtered} height={540} onReady={(cy) => { cyRef.current = cy }}
                  onSelectNode={(id) => { setSelectedNode(id); setSelectedEdge(null) }}
                  onSelectEdge={(id) => { setSelectedEdge(id); setSelectedNode(null) }}
                  onBackgroundClick={() => { setSelectedNode(null); setSelectedEdge(null) }}
                  highlightPath={pathNodes} communities={communities} showCommunities={showCommunities}
                />
              )}
              {filtered && filtered.counts.nodes === 0 && graph.data?.sufficient && (
                <EmptyState title={t.analysis.net.noMatch} icon="filter"
                  action={<Button size="sm" icon="reset" onClick={() => setFilters({ ...DEFAULT_FILTERS, caseId: activeCase })}>{t.common.clearFilters}</Button>} />
              )}
            </div>
          </section>

          {/* ── structural rankings: the explainable A2 output ───────────── */}
          {analysis && analysis.sufficient && (
            <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
              <Card solid title={t.analysis.net.degree} icon="target" subtitle={t.analysis.net.degreeSub}>
                <RankList items={analysis.degree_centrality} onSelect={setSelectedNode} />
              </Card>
              <Card solid title={t.analysis.net.betweenness} icon="branch" subtitle={t.analysis.net.betweennessSub}>
                <RankList items={analysis.betweenness_centrality} onSelect={setSelectedNode} />
              </Card>
              <Card solid title={t.analysis.net.communities} icon="entities"
                subtitle={t.analysis.net.communitiesSub(analysis.community_algorithm, String(analysis.modularity ?? '—'))}>
                {analysis.communities.length === 0 ? (
                  <EmptyState title={t.analysis.net.noRanked} icon="entities" />
                ) : (
                  <ul className="space-y-2">
                    {analysis.communities.map((c: any) => (
                      <li key={c.community_id} className="rounded-[12px] border border-[var(--color-border)] px-3 py-2">
                        <p className="text-[12.5px] font-semibold text-[var(--color-primary-deep)]">
                          Cluster {c.community_id} · <span className="data-num">{c.size}</span> entities
                        </p>
                        <p className="mt-0.5 truncate text-[11.5px] text-[var(--color-text-muted)]">
                          {c.members.slice(0, 5).map((m: any) => m.label).join(', ')}{c.members.length > 5 ? '…' : ''}
                        </p>
                      </li>
                    ))}
                  </ul>
                )}
              </Card>
              <div className="lg:col-span-3">
                <p className="banner-honesty flex items-start gap-2 px-3.5 py-2.5 text-[12px]">
                  <Icon name="info" size={13} />
                  <span>
                    {analysis.safety_note} Engine: {analysis.engine}. Density <span className="data-num">{analysis.density}</span>;{' '}
                    <span className="data-num">{analysis.components}</span> connected component(s).
                  </span>
                </p>
              </div>
            </div>
          )}
          {analysis && !analysis.sufficient && <InsufficientEvidence message={analysis.message} />}
        </div>

        {/* ── inspector column: the drawer is glass, its content is not ──── */}
        <div className="xl:sticky xl:top-[112px] xl:h-[calc(100vh-152px)]">
          {selectedNode && (
            <EntityPanel
              entityId={selectedNode}
              onClose={() => setSelectedNode(null)}
              onSelectEntity={(id) => setSelectedNode(id)}
              onChanged={graph.reload}
              structuralExplanation={explanations[selectedNode]}
              analysisReady={Boolean(analysis?.sufficient)}
              onRunAnalysis={can('analysis:run') ? runAnalysis : undefined}
              analysing={analysing}
            />
          )}
          {selectedEdge && (
            <RelationshipPanel relationshipId={selectedEdge} onClose={() => setSelectedEdge(null)} onChanged={graph.reload} />
          )}
          {!selectedNode && !selectedEdge && (
            <Card title={t.analysis.net.inspector} icon="eye">
              <SectionHeader>{t.analysis.net.inspectorNode}</SectionHeader>
              <p className="text-[13px] leading-relaxed text-[var(--color-text-muted)]">
                {t.analysis.net.inspectorIntroA} <span className="font-semibold text-[var(--color-text)]">{t.analysis.net.inspectorNode}</span>{' '}
                {t.analysis.net.inspectorIntroB}
                <span className="font-semibold text-[var(--color-text)]"> {t.analysis.net.inspectorEdge}</span>{' '}
                {t.analysis.net.inspectorIntroC}
              </p>
              <ul className="mt-3 space-y-2">
                {t.analysis.net.inspectorTips.map((tip) => (
                  <li key={tip} className="flex items-start gap-2 text-[12.5px] text-[var(--color-text)]">
                    <span className="mt-0.5 text-[var(--color-primary)]"><Icon name="check" size={13} /></span>{tip}
                  </li>
                ))}
              </ul>
              {!analysis && can('analysis:run') && (
                <Button size="sm" variant="outline" className="mt-4 w-full" icon="spark" loading={analysing} onClick={runAnalysis}>
                  {t.analysis.net.runAnalysis}
                </Button>
              )}
            </Card>
          )}
        </div>
      </div>
    </>
  )
}

function ChipRow({ label, values, selected, onToggle, kind }: { label: string; values: string[]; selected: string[]; onToggle: (v: string) => void; kind: 'entityType' | 'relationshipType' | 'supportLevel' }) {
  const { t, tok } = useI18n()
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <span className="mr-1 text-[11px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">{label}</span>
      {values.map((v) => {
        const on = selected.includes(v)
        return (
          <button
            key={v}
            onClick={() => onToggle(v)}
            aria-pressed={on}
            className={`focus-ring rounded-md px-2 py-1 text-[11px] font-semibold transition ${
              on
                ? 'bg-[var(--color-primary)] text-white'
                : 'border border-[var(--color-border)] bg-[var(--color-surface-solid)] text-[var(--color-text)] hover:border-[var(--color-primary)]'
            }`}
          >
            {tok(t.tokens[kind], v)}
          </button>
        )
      })}
    </div>
  )
}

function RankList({ items, onSelect }: { items: any[]; onSelect: (id: string) => void }) {
  const { t } = useI18n()
  if (!items?.length) return <EmptyState title={t.analysis.net.noRanked} icon="target" />
  return (
    <ol className="space-y-2">
      {items.slice(0, 6).map((i) => (
        <li key={i.entity_id}>
          <button
            onClick={() => onSelect(i.entity_id)}
            className="focus-ring w-full rounded-[12px] border border-[var(--color-border)] bg-[var(--color-surface-solid)] px-3 py-2.5 text-left transition hover:border-[var(--color-primary)]"
          >
            <div className="flex items-center justify-between gap-2">
              <span className="truncate text-[12.5px] font-semibold text-[var(--color-text)]">
                <span className="data-num text-[var(--color-text-muted)]">{i.rank}.</span> {i.label}
              </span>
              <span className="data-num shrink-0 rounded-md bg-[var(--color-primary-soft)] px-1.5 py-0.5 text-[11.5px] font-semibold text-[var(--color-primary-deep)]">
                {i.score}
              </span>
            </div>
            <p className="mt-1 text-[11.5px] leading-snug text-[var(--color-text-muted)]">{i.interpretation}</p>
          </button>
        </li>
      ))}
    </ol>
  )
}

function Legend() {
  const { t } = useI18n()
  return (
    <div className="hidden flex-wrap items-center gap-3 text-[10.5px] font-semibold text-[var(--color-text-muted)] sm:flex">
      <span className="flex items-center gap-1.5">
        <span className="h-2 w-5 rounded" style={{ background: 'var(--color-success)' }} /> {t.analysis.net.legendHigh}
      </span>
      <span className="flex items-center gap-1.5">
        <span className="h-2 w-5 rounded" style={{ background: 'var(--color-warning)' }} /> {t.analysis.net.legendMedium}
      </span>
      <span className="flex items-center gap-1.5">
        <span className="h-2 w-5 rounded border border-[var(--color-text-muted)]" /> {t.analysis.net.legendLow}
      </span>
      <span className="flex items-center gap-1.5">
        <span className="h-0.5 w-5 border-t-2 border-dashed border-[var(--color-text-muted)]" /> {t.analysis.net.legendUnverified}
      </span>
    </div>
  )
}
```

---

## Files touched

| file | bugs | change |
| --- | --- | --- |
| `frontend/src/components/layout/AppLayout.tsx` | 1, 2 | height chain (`lg:flex` + `flex-col overflow-hidden` aside, `min-h-0 flex-1` nav), bottom fade + guarded scroll-into-view, three overlays → `.glass-solid` |
| `frontend/src/index.css` | 2 | new `.glass-solid` overlay surface (0.97 alpha) |
| `frontend/src/components/layout/LanguageSwitcher.tsx` | 2 | its listbox → `.glass-solid` (same overlay class) |
| `frontend/src/pages/Login.tsx` | 3 | dropped `compact` from the language control |
| `frontend/src/pages/NetworkIntelligence.tsx` | 4 | four fields own cells; checkbox moved to its own full-width row |

No other file was modified; no API contract, route or data shape was touched (all four fixes are
presentation-only).

## FINAL CHECK — `npm run build`

```tsx
vite v8.2.2 building client environment for production...
✓ 71 modules transformed.
dist/index.html                     0.78 kB │ gzip:   0.44 kB
dist/assets/index-BcQwu_Oh.css     75.84 kB │ gzip:  18.63 kB
dist/assets/index-Nzmnwzeg.js   1,305.49 kB │ gzip: 363.58 kB
✓ built in 763ms
```

`scripts/bugfix_verify.sh` — **30/30**:

```text

[1mBUG 1 — nav scrolls, and says so[0m
  PASS  aside is a flex column (was block)
  PASS  aside clips its child (overflow-hidden)
  PASS  aside is display:flex at lg (was block)
  PASS  nav has a definite height (flex-1 min-h-0)
  PASS  min-h-full is gone from the nav
  PASS  nav still scrolls + contains overscroll
  PASS  bottom fade exists and is decoration only
  PASS  fade is conditional on overflow AND not-at-end
  PASS  fade uses the panel surface token
  PASS  scroll-into-view is guarded (only when out of view)
  PASS  scroll-into-view writes only the nav scrollTop
  PASS  it runs on route change
  PASS  active item is tracked by ref
  PASS  NavLink forwards refs (react-router 7.18.3)

[1mBUG 2 — no text bleeds through any overlay[0m
  PASS  .glass-solid defined with 0.97 alpha
  PASS  .glass-solid shipped in the built CSS
  PASS  built alpha is >=0.95 (f2..ff)
  PASS  search results dropdown -> glass-solid
  PASS  notification dropdown -> glass-solid
  PASS  profile dropdown -> glass-solid
  PASS  language listbox -> glass-solid
  PASS  NO absolute-positioned menu uses glass-strong any more
  PASS  glass-strong kept for non-text-critical surfaces

[1mBUG 3 — login language control is labelled[0m
  PASS  Login no longer passes compact
  PASS  Login renders the labelled switcher
  PASS  the label span renders when not compact

[1mBUG 4 — checkbox row is independent of the field grid[0m
  PASS  verifiedOnly checkbox is outside the grid div
  PASS  two date inputs own their own grid cells
  PASS  checkbox sits in its own full-width row
  PASS  checkbox row uses w-fit (label does not stretch/clip)

[1mBUGFIX VERIFICATION: 30 passed, 0 failed[0m
```

