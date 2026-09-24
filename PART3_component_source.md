# PART 3 — full component source (as shipped)

Requested verbatim: the three components the brief names. Each is reproduced complete and
unmodified from the workspace, so this file and the running app cannot drift.

## `frontend/src/pages/Dashboard.tsx`  ·  390 lines

```tsx
import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApp } from '../state/AppContext'
import { useFetch } from '../hooks/useFetch'
import type { DashboardPayload } from '../types'
import NetworkGraph from '../components/graph/NetworkGraph'
import AgentRunModal from '../components/agents/AgentRunModal'
import { Icon } from '../components/shared/Icon'
import {
  Badge, Button, Card, EmptyState, ErrorState, Hash, InsufficientEvidence, KeyValue,
  KpiCard, LoadingBlock, PageHeader, Principle, SectionHeader, StatusBadge, StatusPill, SupportBadge,
} from '../components/shared/ui'
import { useI18n } from '../i18n/LanguageContext'

/* ============================================================================
   DASHBOARD — command centre
   KPI cards are glass (low text density, at-a-glance). Every list, feed and
   table sits on a solid surface so small text stays crisp. Every tile is a real
   link into the analysis that produced the number; nothing here is decorative.
   ============================================================================ */

const FLOW = [
  { key: 'evidence', icon: 'evidence', to: '/evidence' },
  { key: 'entities', icon: 'entities', to: '/entities' },
  { key: 'network', icon: 'network', to: '/network' },
  { key: 'temporal', icon: 'timeline', to: '/timeline' },
  { key: 'corroboration', icon: 'hypotheses', to: '/hypotheses' },
  { key: 'gaps', icon: 'gaps', to: '/information-gaps' },
  { key: 'nextAction', icon: 'nextbest', to: '/next-best-action' },
  { key: 'validation', icon: 'shield', to: '/audit' },
] as const

export default function Dashboard() {
  const { t, tok, fmt } = useI18n()
  const { activeCase, user, cases } = useApp()
  const navigate = useNavigate()
  const [runOpen, setRunOpen] = useState(false)

  const path = `/api/dashboard${activeCase ? `?case_id=${activeCase}` : ''}`
  const { data, loading, error, reload } = useFetch<DashboardPayload>(path, [activeCase])
  const scope = useMemo(() => (activeCase ? [activeCase] : []), [activeCase])

  const caseTitle = activeCase ? cases.find((c) => c.case_id === activeCase)?.title : null

  return (
    <>
      <PageHeader
        tagline={t.pages.dashboard.tagline}
        title={t.pages.dashboard.title}
        description={
          activeCase
            ? t.dashboard.contextCase(activeCase, caseTitle || '')
            : t.dashboard.contextAll
        }
      >
        <Button icon="refresh" onClick={reload}>{t.dashboard.refresh}</Button>
        <Button variant="primary" icon="play" onClick={() => setRunOpen(true)}>{t.dashboard.runFullAnalysis}</Button>
      </PageHeader>

      {loading && <LoadingBlock label={t.dashboard.loading} rows={4} variant="cards" />}
      {error && <ErrorState message={error} onRetry={reload} />}

      {data && (
        <div className="space-y-8">
          {/* ── KPI row — glass, six real figures, each links to its source ── */}
          <section>
            <SectionHeader>{t.pages.dashboard.title}</SectionHeader>
            <div className="stagger grid grid-cols-2 gap-4 lg:grid-cols-3 xl:grid-cols-6">
              <KpiCard label={t.dashboard.kpiActiveCases} value={data.kpis.active_cases} icon="cases"
                hint={t.dashboard.kpiActiveCasesHint(data.kpis.total_cases)} onClick={() => navigate('/cases')} />
              <KpiCard label={t.dashboard.kpiEvidence} value={data.kpis.evidence_items} icon="evidence" tone="navy"
                hint={t.dashboard.kpiEvidenceHint} onClick={() => navigate('/evidence')} />
              <KpiCard label={t.dashboard.kpiCandidateRels} value={data.kpis.candidate_relationships} icon="network" tone="amber"
                hint={t.dashboard.kpiCandidateRelsHint} onClick={() => navigate('/network')} />
              <KpiCard label={t.dashboard.kpiCrossCase} value={data.kpis.cross_case_links} icon="crosscase" tone="violet"
                hint={t.dashboard.kpiCrossCaseHint} onClick={() => navigate('/cross-case')} />
              <KpiCard label={t.dashboard.kpiGaps} value={data.kpis.information_gaps} icon="gaps" tone="red"
                hint={t.dashboard.kpiGapsHint} onClick={() => navigate('/information-gaps')} />
              <KpiCard label={t.dashboard.kpiPending} value={data.kpis.pending_verifications} icon="shield" tone="green"
                hint={t.dashboard.kpiPendingHint} onClick={() => navigate('/network')} />
            </div>
          </section>

          {/* ── pipeline + activity feed ─────────────────────────────────── */}
          <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1.45fr_1fr]">
            <Card title={t.dashboard.pipelineTitle} icon="branch" subtitle={t.dashboard.pipelineSubtitle}>
              <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
                {data.pipeline.map((p, i) => (
                  <div key={p.stage} className="surface-solid relative px-4 py-3">
                    <p className="section-header !text-[11.5px]">{tok(t.tokens.pipelineStage, p.stage)}</p>
                    <p className="data-num mt-1.5 text-[26px] font-semibold leading-none text-[var(--color-primary-deep)]">{p.value}</p>
                    <p className="mt-1.5 text-[12px] leading-snug text-[var(--color-text-muted)]">{p.detail}</p>
                    {i < data.pipeline.length - 1 && (
                      <span className="absolute -right-3 top-1/2 hidden -translate-y-1/2 text-[var(--color-primary)]/50 md:block">
                        <Icon name="arrowRight" size={18} />
                      </span>
                    )}
                  </div>
                ))}
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                {FLOW.map((f, i) => (
                  <button
                    key={f.key}
                    onClick={() => navigate(f.to)}
                    className="focus-ring flex items-center gap-1.5 rounded-[10px] border border-[var(--color-border)] bg-[var(--color-surface-solid)] px-2.5 py-1.5 text-[12px] font-semibold text-[var(--color-text)] transition hover:border-[var(--color-primary)] hover:text-[var(--color-primary-deep)]"
                  >
                    <span className="text-[var(--color-primary)]"><Icon name={f.icon as any} size={13} /></span>
                    {t.dashboard.flow[f.key]}
                    {i < FLOW.length - 1 && <span className="text-[var(--color-text-muted)]">›</span>}
                  </button>
                ))}
              </div>
            </Card>

            {/* activity feed: what the system actually did, most recent first */}
            <Card
              title={t.dashboard.recentAudit}
              icon="audit"
              subtitle={t.dashboard.integritySub}
              solid
              actions={<Button size="sm" icon="arrowRight" onClick={() => navigate('/audit')}>{t.dashboard.fullTrail}</Button>}
            >
              {data.recent_audit.length === 0 ? (
                <EmptyState title={t.dashboard.recentAudit} message={t.dashboard.pendingValidationNone} icon="audit" />
              ) : (
                <ol className="relative space-y-3 pl-5">
                  <span className="absolute bottom-1 left-[5px] top-2 w-px bg-[var(--color-border)]" aria-hidden />
                  {data.recent_audit.slice(0, 8).map((a) => (
                    <li key={a.audit_id} className="relative">
                      <span className="absolute -left-5 top-1.5 h-2.5 w-2.5 rounded-full border-2 border-[var(--color-surface-solid)] bg-[var(--color-primary)]" />
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="mono-id text-[11px] text-[var(--color-text-muted)]">{a.timestamp.slice(11, 19)}</span>
                        <Badge tone="blue">{tok(t.tokens.auditAction, a.action)}</Badge>
                        <span className="text-[11px] font-semibold text-[var(--color-text-muted)]">{a.user_id}</span>
                      </div>
                      <p className="mt-0.5 break-words text-[12.5px] text-[var(--color-text)]">{a.detail || a.object_id}</p>
                    </li>
                  ))}
                </ol>
              )}
            </Card>
          </div>

          {/* ── graph preview + findings + integrity ─────────────────────── */}
          <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1.45fr_1fr]">
            <Card
              title={t.dashboard.networkPreview}
              icon="network"
              subtitle={t.dashboard.networkPreviewSub(data.network_preview.counts.nodes, data.network_preview.counts.edges)}
              solid
              actions={<Button size="sm" icon="arrowRight" onClick={() => navigate('/network')}>{t.dashboard.openNetwork}</Button>}
            >
              {data.network_preview.sufficient ? (
                <NetworkGraph
                  payload={data.network_preview}
                  height={340}
                  onSelectNode={() => navigate('/network')}
                  onSelectEdge={() => navigate('/network')}
                />
              ) : (
                <InsufficientEvidence message={data.network_preview.message} />
              )}
            </Card>

            <div className="space-y-4">
              <Card title={t.dashboard.findings} icon="hypotheses" subtitle={t.dashboard.findingsSub} solid
                actions={<Button size="sm" onClick={() => navigate('/hypotheses')}>{t.dashboard.allFindings}</Button>}>
                {data.findings.length === 0 && <InsufficientEvidence message={t.dashboard.findingsNone} />}
                <ul className="space-y-2.5">
                  {data.findings.slice(0, 3).map((f) => (
                    <li key={f.lead_id} className="rounded-[12px] border border-[var(--color-border)] px-3.5 py-3">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <p className="text-[13.5px] font-semibold text-[var(--color-primary-deep)]">{f.title}</p>
                        <StatusBadge status={f.status} />
                      </div>
                      <ul className="mt-2 space-y-1">
                        {f.why.slice(0, 3).map((w) => (
                          <li key={w} className="flex items-start gap-1.5 text-[12.5px] text-[var(--color-text)]">
                            <span className="mt-0.5 text-[var(--color-success)]"><Icon name="check" size={12} /></span>{w}
                          </li>
                        ))}
                      </ul>
                      {f.missing_evidence.length > 0 && (
                        <p className="mt-2 text-[12px] text-[var(--color-warning)]">
                          {t.dashboard.missing}: {f.missing_evidence.slice(0, 2).join('; ')}
                        </p>
                      )}
                    </li>
                  ))}
                </ul>
              </Card>

              <Card title={t.dashboard.integrity} icon="shield" subtitle={t.dashboard.integritySub} solid
                actions={<Button size="sm" onClick={() => navigate('/audit')}>{t.dashboard.auditShort}</Button>}>
                <div className="grid grid-cols-2 gap-3">
                  <MiniStat
                    label={t.dashboard.objectsVerified}
                    value={`${data.integrity.verified}/${data.integrity.total}`}
                    tone={data.integrity.mismatches.length ? 'amber' : 'green'}
                  />
                  <MiniStat
                    label={t.dashboard.ledgerBlocks}
                    value={data.integrity.ledger_blocks}
                    tone={data.integrity.ledger_intact ? 'green' : 'red'}
                  />
                </div>
                <div className="mt-3 flex flex-wrap items-center gap-2 text-[12px] text-[var(--color-text-muted)]">
                  {t.dashboard.chainHead} <Hash value={data.integrity.head_hash} chars={18} />
                  <StatusPill status={data.integrity.ledger_intact ? 'VERIFIED' : 'REJECTED'}
                    label={data.integrity.ledger_intact ? t.dashboard.chainIntact : t.dashboard.chainBroken} />
                </div>
                {data.integrity.mismatches.length > 0 && (
                  <p className="mt-3 rounded-[12px] border border-[var(--color-danger)] bg-[rgba(196,52,31,0.06)] px-3 py-2 text-[12.5px] text-[var(--color-danger)]">
                    <span className="font-bold">Integrity mismatch:</span> {data.integrity.mismatches.join(', ')} — the stored object
                    no longer matches its registered hash.
                  </p>
                )}
              </Card>
            </div>
          </div>

          {/* ── timeline + recent evidence ──────────────────────────────── */}
          <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            <Card title={t.dashboard.timelinePreview} icon="timeline" subtitle={t.dashboard.timelinePreviewSub} solid
              actions={<Button size="sm" onClick={() => navigate('/timeline')}>{t.dashboard.fullTimeline}</Button>}>
              {data.timeline_preview.length === 0 ? (
                <EmptyState title={t.dashboard.timelineNone} icon="clock" />
              ) : (
                <ol className="relative space-y-3 border-l-2 border-[var(--color-primary-soft)] pl-4">
                  {data.timeline_preview.slice(0, 6).map((e) => (
                    <li key={e.event_id} className="relative">
                      <span className="absolute -left-[22px] top-1.5 h-2.5 w-2.5 rounded-full border-2 border-[var(--color-surface-solid)] bg-[var(--color-primary)]" />
                      <p className="text-[13px] font-semibold text-[var(--color-text)]">{e.title}</p>
                      <p className="text-[11.5px] text-[var(--color-text-muted)]">
                        {fmt.dateTime(e.timestamp)} · {e.case_id} · <span className="mono-id">{e.evidence_id || t.dashboard.noEvidenceRef}</span>
                      </p>
                    </li>
                  ))}
                </ol>
              )}
            </Card>

            <Card title={t.dashboard.recentEvidence} icon="evidence" subtitle={t.dashboard.recentEvidenceSub} solid
              actions={<Button size="sm" onClick={() => navigate('/evidence')}>{t.dashboard.evidenceRegistry}</Button>}>
              {data.recent_evidence.length === 0 ? (
                <EmptyState title={t.dashboard.evidenceNone} icon="evidence" />
              ) : (
                <ul className="divide-y divide-[var(--color-border)]">
                  {data.recent_evidence.map((e) => (
                    <li key={e.evidence_id} className="flex flex-wrap items-center justify-between gap-2 py-2.5 first:pt-0">
                      <button
                        onClick={() => navigate(`/evidence?focus=${e.evidence_id}`)}
                        className="focus-ring min-w-0 rounded text-left"
                      >
                        <p className="truncate text-[13px] font-semibold text-[var(--color-text)]">
                          <span className="mono-id">{e.evidence_id}</span> · {tok(t.tokens.evidenceType, e.evidence_type)}
                        </p>
                        <p className="truncate text-[11.5px] text-[var(--color-text-muted)]">{e.source} · {e.case_id} · {fmt.date(e.timestamp)}</p>
                      </button>
                      <div className="flex shrink-0 gap-1.5">
                        <StatusBadge status={e.integrity_status} />
                        <StatusBadge status={e.processing_status} />
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          </div>

          {/* ── validation queue + gaps + next analysis ─────────────────── */}
          <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
            <Card title={t.dashboard.pendingValidation} icon="shield" subtitle={t.dashboard.pendingValidationSub} solid>
              {data.pending_validation.length === 0 ? (
                <EmptyState title={t.dashboard.pendingValidationNone} icon="check" />
              ) : (
                <ul className="space-y-2">
                  {data.pending_validation.slice(0, 5).map((p: any) => (
                    <li key={p.relationship_id} className="rounded-[12px] border border-[var(--color-border)] px-3 py-2.5">
                      <p className="text-[12.5px] font-semibold text-[var(--color-text)]">{p.source_label} → {p.target_label}</p>
                      <div className="mt-1 flex flex-wrap items-center gap-1.5 text-[11.5px] text-[var(--color-text-muted)]">
                        <Badge tone="slate">{tok(t.tokens.relationshipType, p.relationship_type)}</Badge>
                        <SupportBadge level={p.support_level} />
                        <span className="mono-id">{p.case_id} · {p.evidence_id}</span>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
              <Button size="sm" className="mt-3 w-full" icon="arrowRight" onClick={() => navigate('/network')}>
                {t.dashboard.reviewInGraph}
              </Button>
            </Card>

            <Card title={t.dashboard.gapsTitle} icon="gaps" subtitle={t.dashboard.gapsSub} solid>
              {data.information_gaps.length === 0 ? (
                <EmptyState title={t.dashboard.gapsNone} icon="gaps" />
              ) : (
                <ul className="space-y-2">
                  {data.information_gaps.slice(0, 3).map((g) => (
                    <li key={g.gap_id} className="rounded-[12px] border border-dashed border-[var(--color-text-muted)] px-3 py-2.5">
                      <div className="flex items-center justify-between gap-2">
                        <p className="mono-id text-[12px] font-semibold text-[var(--color-text)]">{g.gap_id}</p>
                        <Badge tone={g.severity === 'HIGH' ? 'red' : g.severity === 'MEDIUM' ? 'amber' : 'slate'}>
                          {tok(t.tokens.priority, g.severity)}
                        </Badge>
                      </div>
                      <p className="mt-1 text-[12.5px] text-[var(--color-text)]">{g.statement}</p>
                      <p className="mt-1 text-[11.5px] text-[var(--color-text-muted)]">? {g.unknown.slice(0, 2).join(' · ')}</p>
                    </li>
                  ))}
                </ul>
              )}
              <Button size="sm" className="mt-3 w-full" icon="arrowRight" onClick={() => navigate('/information-gaps')}>
                {t.dashboard.allGaps}
              </Button>
            </Card>

            <Card title={t.dashboard.nextAnalysis} icon="nextbest" subtitle={t.dashboard.nextAnalysisSub} solid>
              {data.next_best_action ? (
                <>
                  <div className="rounded-[12px] border border-[var(--color-primary)] bg-[var(--color-primary-soft)] px-3.5 py-3">
                    <div className="flex items-center justify-between gap-2">
                      <Badge tone="blue">{t.dashboard.rank1}</Badge>
                      <span className="data-num text-[12px] font-semibold text-[var(--color-primary-deep)]">
                        {t.dashboard.infoValue(Math.round((data.next_best_action.information_value || 0) * 100))}
                      </span>
                    </div>
                    <p className="mt-2 text-[13.5px] font-semibold text-[var(--color-primary-deep)]">{data.next_best_action.title}</p>
                    <p className="mt-1 text-[12.5px] leading-relaxed text-[var(--color-text)]">{data.next_best_action.rationale}</p>
                  </div>
                  <ul className="mt-2.5 space-y-1.5">
                    {data.next_best_actions.slice(1, 4).map((a) => (
                      <li key={a.action_id} className="flex items-center justify-between gap-2 rounded-[10px] border border-[var(--color-border)] px-3 py-1.5 text-[12.5px] text-[var(--color-text)]">
                        <span className="truncate">{a.rank}. {a.title}</span>
                        <span className="data-num shrink-0 font-semibold text-[var(--color-primary)]">
                          {Math.round(a.information_value * 100)}%
                        </span>
                      </li>
                    ))}
                  </ul>
                </>
              ) : (
                <EmptyState title={t.dashboard.nextAnalysisNone} icon="target" />
              )}
              <Button size="sm" className="mt-3 w-full" icon="arrowRight" onClick={() => navigate('/next-best-action')}>
                {t.dashboard.openDecisionSupport}
              </Button>
            </Card>
          </div>

          {/* ── principle + operator context ────────────────────────────── */}
          <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1fr_1.4fr]">
            <Principle />
            <Card title={t.common.details} icon="user" solid>
              <KeyValue
                items={[
                  [t.nav.caseAccess, user?.case_access.includes('*') ? t.nav.allCases : (user?.case_access.join(', ') || t.common.none)],
                  [t.common.role, tok(t.tokens.role, user?.role)],
                  [t.dashboard.chainHead, <Hash value={data.integrity.head_hash} chars={24} />],
                ]}
              />
              <p className="mt-4 text-center text-[11.5px] leading-relaxed text-[var(--color-text-muted)]">
                {t.dashboard.signedInAs(user?.display_name || '', tok(t.tokens.role, user?.role), data.product.classification)}
              </p>
            </Card>
          </div>
        </div>
      )}

      <AgentRunModal open={runOpen} onClose={() => { setRunOpen(false); reload() }}
        objective="FULL_CASE_ANALYSIS" caseIds={scope} />
    </>
  )
}

function MiniStat({ label, value, tone }: { label: string; value: React.ReactNode; tone: 'green' | 'amber' | 'red' }) {
  const tones: Record<string, string> = {
    green: 'border-[var(--color-success)] bg-[rgba(30,142,90,0.07)]',
    amber: 'border-[var(--color-warning)] bg-[rgba(184,121,26,0.08)]',
    red: 'border-[var(--color-danger)] bg-[rgba(196,52,31,0.07)]',
  }
  return (
    <div className={`rounded-[12px] border px-3 py-2 ${tones[tone]}`}>
      <p className="text-[10.5px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">{label}</p>
      <p className="data-num mt-1 text-[19px] font-semibold text-[var(--color-primary-deep)]">{value}</p>
    </div>
  )
}
```

## `frontend/src/pages/NetworkIntelligence.tsx`  ·  387 lines

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
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
              <TextInput placeholder={t.analysis.net.searchEntity} value={filters.search}
                onChange={(e) => setFilters({ ...filters, search: e.target.value })} />
              <Select value={filters.caseId || ''} onChange={(e) => setFilters({ ...filters, caseId: e.target.value || null })}>
                <option value="">{t.analysis.net.allAuthorizedCases}</option>
                {cases.map((c) => <option key={c.case_id} value={c.case_id}>{c.case_id}</option>)}
              </Select>
              <div className="flex items-center gap-2">
                <TextInput type="date" value={filters.dateFrom || ''} onChange={(e) => setFilters({ ...filters, dateFrom: e.target.value })} />
                <TextInput type="date" value={filters.dateTo || ''} onChange={(e) => setFilters({ ...filters, dateTo: e.target.value })} />
              </div>
              <label className="flex items-center gap-2 text-[12.5px] font-semibold text-[var(--color-text)]">
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

## `frontend/src/pages/Evidence.tsx`  ·  564 lines

```tsx
import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useApp } from '../state/AppContext'
import { useFetch } from '../hooks/useFetch'
import { api, ApiError } from '../services/api'
import { Icon } from '../components/shared/Icon'
import {
  Badge, Button, Card, EmptyState, ErrorState, Field, Hash, LoadingBlock,
  Modal, PageHeader, ProvenanceStrip, SectionHeader, Select, SourceTrustBadge, StatusPill,
  SupportBadge, Td, TextArea, TextInput, Th,
} from '../components/shared/ui'
import type { EvidenceItem } from '../types'
import { useI18n } from '../i18n/LanguageContext'

/* ============================================================================
   EVIDENCE WORKSPACE
   The registry table and the document reading panel are SOLID surfaces: this is
   the densest text in the product and blurred glass would hurt it. Glass is used
   only for the provenance strip above the reading panel (short labels, high
   contrast) and for the register-evidence modal.

   Identifiers and hashes are monospace + tabular so they can be read character
   by character and compared against a printed record.
   ============================================================================ */

const TYPES = ['FIR', 'POLICE_REPORT', 'CDR', 'FINANCIAL_RECORD', 'SURVEILLANCE_REPORT', 'INTELLIGENCE_REPORT', 'IMAGE', 'PDF', 'CSV']
const PIPELINE = ['UPLOADED', 'PROCESSING', 'EXTRACTED', 'ENTITIES_FOUND', 'RELATIONSHIPS_CANDIDATE']
const MASKABLE_ENTITIES = ['PHONE', 'ACCOUNT', 'DEVICE']

export default function Evidence() {
  const { t, tok, fmt } = useI18n()
  const { cases, activeCase, can, notify } = useApp()
  const [params, setParams] = useSearchParams()
  const focus = params.get('focus')
  const caseFilter = params.get('case') || activeCase || ''

  const list = useFetch<EvidenceItem[]>(`/api/evidence${caseFilter ? `?case_id=${caseFilter}` : ''}`, [caseFilter])
  const [selected, setSelected] = useState<string | null>(focus)
  const [uploadOpen, setUploadOpen] = useState(false)
  const [typeFilter, setTypeFilter] = useState('')
  const [busy, setBusy] = useState<string | null>(null)
  const [support, setSupport] = useState<any>(null)
  const [supportBusy, setSupportBusy] = useState(false)

  useEffect(() => { if (focus) setSelected(focus) }, [focus])
  useEffect(() => { setSupport(null) }, [selected])

  const rows = useMemo(
    () => (list.data || []).filter((e) => !typeFilter || e.evidence_type === typeFilter),
    [list.data, typeFilter],
  )

  const detail = useFetch<any>(selected ? `/api/evidence/${selected}` : null, [selected])

  async function act(kind: 'process' | 'integrity-check' | 'verify' | 'reject', id: string, body?: unknown) {
    setBusy(id + kind)
    try {
      const res = await api.post<any>(`/api/evidence/${id}/${kind}`, body ?? {})
      if (kind === 'process') {
        notify('success', `${id}: document pipeline complete`,
          `${res.extraction?.entities?.length ?? 0} entities · ${res.graph_updates?.relationships?.length ?? 0} candidate relationships`)
      } else if (kind === 'integrity-check') {
        notify(res.status === 'VERIFIED' ? 'success' : 'error', `${id}: ${res.status}`, res.message)
      } else {
        notify('success', `${id} ${kind === 'verify' ? 'human-verified' : 'rejected'}`, 'Recorded in audit trail and ledger.')
      }
      list.reload(); if (selected === id) detail.reload()
    } catch (err) {
      notify('error', 'Action failed', err instanceof ApiError ? err.message : undefined)
    } finally { setBusy(null) }
  }

  /** A7 — ask the same weighting function the corroboration engine uses. */
  async function checkSupport() {
    if (!selected) return
    setSupportBusy(true)
    try {
      setSupport(await api.post<any>('/api/analysis/evidence-support', { evidence_ids: [selected] }))
    } catch (err) {
      notify('error', 'Could not compute corroboration weight', err instanceof ApiError ? err.message : undefined)
    } finally { setSupportBusy(false) }
  }

  const ev = detail.data?.evidence

  return (
    <>
      <PageHeader
        tagline={t.pages.evidence.tagline}
        title={t.pages.evidence.title}
        description={t.pages.evidence.description}
      >
        <Select value={caseFilter} onChange={(e) => setParams(e.target.value ? { case: e.target.value } : {})} className="w-48">
          <option value="">{t.evidence.allAuthorizedCases}</option>
          {cases.map((c) => <option key={c.case_id} value={c.case_id}>{c.case_id}</option>)}
        </Select>
        <Button icon="refresh" onClick={list.reload}>{t.evidence.refresh}</Button>
        {can('evidence:upload') && (
          <Button variant="primary" icon="upload" onClick={() => setUploadOpen(true)}>{t.evidence.upload}</Button>
        )}
      </PageHeader>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-[1.3fr_1fr]">
        {/* ── registry table (solid surface) ─────────────────────────────── */}
        <section className="surface-solid self-start">
          <header className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--color-border)] px-5 py-3.5">
            <div className="flex items-center gap-2">
              <span className="text-[var(--color-primary)]"><Icon name="evidence" size={16} /></span>
              <h2 className="section-header !text-[13px]">{t.evidence.itemsTitle(rows.length)}</h2>
            </div>
            <Select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)} className="w-44">
              <option value="">{t.evidence.allTypes}</option>
              {TYPES.map((et) => <option key={et} value={et}>{tok(t.tokens.evidenceType, et)}</option>)}
            </Select>
          </header>
          <div className="p-5">
            {list.loading && <LoadingBlock label={t.evidence.loading} variant="table" />}
            {list.error && <ErrorState message={list.error} onRetry={list.reload} />}
            {!list.loading && rows.length === 0 && (
              <EmptyState title={t.evidence.noneInScope} message={t.evidence.noneInScopeGap} icon="evidence"
                action={can('evidence:upload')
                  ? <Button size="sm" variant="primary" icon="upload" onClick={() => setUploadOpen(true)}>{t.evidence.upload}</Button>
                  : undefined} />
            )}
            {rows.length > 0 && (
              <div className="-mx-5 overflow-x-auto">
                <table className="w-full min-w-[680px] border-collapse text-left text-[13px]">
                  <thead>
                    <tr>
                      <Th>{t.evidence.thEvidence}</Th><Th>{t.evidence.thTypeSource}</Th><Th>{t.evidence.thCase}</Th>
                      <Th>{t.evidence.thProcessing}</Th><Th>{t.evidence.thIntegrity}</Th><Th>{t.evidence.thHash}</Th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((e) => {
                      const active = selected === e.evidence_id
                      return (
                        <tr
                          key={e.evidence_id}
                          onClick={() => setSelected(e.evidence_id)}
                          className={`cursor-pointer transition ${active ? 'bg-[var(--color-primary-soft)]' : 'hover:bg-[var(--color-primary-soft)]/50'}`}
                        >
                          <Td className="border-l-2" >
                            <span className="flex items-start gap-2">
                              <span className={`mt-1 h-3 w-[3px] shrink-0 rounded ${active ? 'bg-[var(--color-primary)]' : 'bg-transparent'}`} />
                              <span>
                                <span className="mono-id font-semibold text-[var(--color-primary-deep)]">{e.evidence_id}</span>
                                <br /><span className="text-[11px] text-[var(--color-text-muted)]">{fmt.dateTime(e.timestamp)}</span>
                              </span>
                            </span>
                          </Td>
                          <Td>
                            {tok(t.tokens.evidenceType, e.evidence_type)}
                            <br /><span className="text-[11px] text-[var(--color-text-muted)]">{e.source}</span>
                          </Td>
                          <Td><span className="mono-id">{e.case_id}</span></Td>
                          <Td><StatusPill status={e.processing_status} /></Td>
                          <Td><StatusPill status={e.integrity_status} /></Td>
                          <Td><Hash value={e.sha256} chars={10} /></Td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </section>

        {/* ── detail column ─────────────────────────────────────────────── */}
        <div className="space-y-5">
          {!selected && (
            <Card title={t.evidence.detailTitle} icon="doc" solid>
              <EmptyState title={t.evidence.detailEmpty} icon="search"
                message="Select a row in the registry to open its content, extraction and chain of custody." />
            </Card>
          )}

          {selected && detail.loading && (
            <Card title={t.evidence.detailTitle} icon="doc" solid><LoadingBlock rows={3} variant="table" /></Card>
          )}
          {selected && detail.error && (
            <Card title={t.evidence.detailTitle} icon="doc" solid><ErrorState message={detail.error} onRetry={detail.reload} /></Card>
          )}

          {selected && ev && (
            <>
              {/* glass provenance strip — short labels only, never body copy */}
              <ProvenanceStrip
                items={[
                  ['Evidence ID', <span key="id" className="mono-id font-semibold">{ev.evidence_id}</span>],
                  [t.common.type, tok(t.tokens.evidenceType, ev.evidence_type)],
                  [t.common.source, ev.source],
                  [t.common.case, <span key="c" className="mono-id">{ev.case_id}</span>],
                  ['SHA-256', <Hash key="h" value={ev.sha256} chars={20} />],
                  [t.common.status, <StatusPill key="s" status={ev.integrity_status} />],
                ]}
              />

              <section className="surface-solid">
                <header className="flex flex-wrap items-start justify-between gap-3 border-b border-[var(--color-border)] px-5 py-3.5">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-[var(--color-primary)]"><Icon name="doc" size={16} /></span>
                      <h2 className="section-header !text-[13px]">
                        {tok(t.tokens.evidenceType, ev.evidence_type)} · <span className="mono-id">{ev.evidence_id}</span>
                      </h2>
                    </div>
                    <p className="mt-1 text-[12.5px] text-[var(--color-text-muted)]">{ev.source} · <span className="mono-id">{ev.case_id}</span></p>
                  </div>
                  <Button size="sm" icon="close" onClick={() => setSelected(null)}>{t.common.close}</Button>
                </header>

                <div className="space-y-5 p-5">
                  <div className="flex flex-wrap items-center gap-1.5">
                    <StatusPill status={ev.integrity_status} />
                    <StatusPill status={ev.verification_status} />
                    <StatusPill status={ev.processing_status} />
                    <Badge tone="slate">{ev.text_origin.replace(/_/g, ' ')}</Badge>
                    {/* honest OCR state — never claim OCR ran when it did not */}
                    <span className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide ${
                      ev.ocr_applied ? 'status-verified' : 'status-candidate'
                    }`}>
                      <Icon name={ev.ocr_applied ? 'check' : 'info'} size={11} />
                      {ev.ocr_applied ? t.evidence.ocrApplied : t.evidence.ocrNotApplied}
                    </span>
                    {ev.source_trust && (
                      <SourceTrustBadge trust={ev.source_trust} weight={ev.source_trust_weight} />
                    )}
                  </div>

                  {/* processing pipeline trace */}
                  <div>
                    <SectionHeader>{t.evidence.processingPipeline}</SectionHeader>
                    <div className="flex flex-wrap items-center gap-1">
                      {PIPELINE.map((stage, i) => {
                        const reached = PIPELINE.indexOf(ev.processing_status) >= i
                        return (
                          <span key={stage} className="flex items-center gap-1">
                            <span className={`rounded-md px-2 py-1 text-[11px] font-semibold ${
                              reached
                                ? 'bg-[var(--color-primary)] text-white'
                                : 'border border-[var(--color-border)] bg-[var(--color-surface-solid)] text-[var(--color-text-muted)]'
                            }`}>
                              {tok(t.tokens.processingStatus, stage)}
                            </span>
                            {i < PIPELINE.length - 1 && <span className="text-[var(--color-text-muted)]">›</span>}
                          </span>
                        )
                      })}
                    </div>
                    <p className="mt-2 flex flex-wrap items-center gap-2 text-[12px] text-[var(--color-text-muted)]">
                      {t.evidence.registeredHash} <Hash value={ev.sha256} chars={32} />
                    </p>
                  </div>

                  {/* actions — every button performs a real, audited operation */}
                  <div className="flex flex-wrap gap-2">
                    {can('evidence:process') && (
                      <Button size="sm" icon="spark" loading={busy === selected + 'process'} onClick={() => act('process', selected)}>
                        {t.evidence.processDocument}
                      </Button>
                    )}
                    {can('evidence:integrity') && (
                      <Button size="sm" icon="hash" loading={busy === selected + 'integrity-check'} onClick={() => act('integrity-check', selected)}>
                        {t.evidence.integrityCheck}
                      </Button>
                    )}
                    {can('analysis:run') && (
                      <Button size="sm" icon="shield" loading={supportBusy} onClick={checkSupport}>
                        Corroboration weight
                      </Button>
                    )}
                    {can('verification:decide') && (
                      <>
                        <Button size="sm" variant="success" icon="check" loading={busy === selected + 'verify'}
                          onClick={() => act('verify', selected, { object_type: 'EVIDENCE', rationale: t.evidence.verifyRationale })}>{t.evidence.verify}</Button>
                        <Button size="sm" variant="danger" icon="reject" loading={busy === selected + 'reject'}
                          onClick={() => act('reject', selected, { object_type: 'EVIDENCE', rationale: t.evidence.rejectRationale })}>{t.evidence.reject}</Button>
                      </>
                    )}
                  </div>

                  {/* A7 corroboration weighting, computed live by the backend */}
                  {support && (
                    <div className="rounded-[12px] border border-[var(--color-border)] bg-[var(--color-primary-soft)] px-3.5 py-3">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <p className="section-header !text-[11.5px]">Source trust &amp; corroboration weight</p>
                        <SupportBadge level={support.support_level_reachable} />
                      </div>
                      <p className="data-num mt-2 text-[12.5px] text-[var(--color-text)]">
                        Weighted support {support.weighted_support?.toFixed?.(2) ?? support.weighted_support} from{' '}
                        {support.independent_sources} independent source(s).
                      </p>
                      <p className="mt-1 text-[12.5px] leading-relaxed text-[var(--color-text)]">{support.explanation}</p>
                      <ul className="mt-2 space-y-1">
                        {(support.sources || []).map((s: any) => (
                          <li key={s.source} className="flex flex-wrap items-center gap-2 text-[11.5px] text-[var(--color-text)]">
                            <SourceTrustBadge trust={s.source_trust} weight={s.weight} />
                            <span>{s.source}</span>
                            <span className="mono-id text-[var(--color-text-muted)]">{s.evidence_ids.join(', ')}</span>
                          </li>
                        ))}
                      </ul>
                      <p className="mt-2 text-[11px] leading-relaxed text-[var(--color-text-muted)]">{support.policy_note}</p>
                    </div>
                  )}

                  {ev.notes && (
                    <p className="flex items-start gap-2 rounded-[12px] border border-[var(--color-warning)] bg-[rgba(184,121,26,0.07)] px-3 py-2 text-[12.5px] text-[var(--color-text)]">
                      <Icon name="info" size={13} /> {ev.notes}
                    </p>
                  )}
                </div>
              </section>

              {/* reading panel — the document itself, on solid, generous type */}
              <section className="surface-solid">
                <header className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--color-border)] px-5 py-3.5">
                  <h2 className="section-header !text-[13px]">{t.evidence.extractedContent}</h2>
                  <span className="data-num text-[11.5px] text-[var(--color-text-muted)]">
                    {t.evidence.charactersInStorage(detail.data.content_length)}
                  </span>
                </header>
                <div className="p-5">
                  {detail.data.content_preview ? (
                    <div className="reading-panel max-h-[380px] overflow-auto whitespace-pre-wrap">{detail.data.content_preview}</div>
                  ) : (
                    <EmptyState title={t.evidence.noTextContent} icon="doc" />
                  )}
                </div>
              </section>

              {/* extraction */}
              {detail.data.extraction && (
                <section className="surface-solid">
                  <header className="border-b border-[var(--color-border)] px-5 py-3.5">
                    <h2 className="section-header !text-[13px]">
                      {t.evidence.entitiesExtracted((Object.values(detail.data.extraction.counts || {}) as number[]).reduce((a, b) => a + b, 0))}
                    </h2>
                  </header>
                  <div className="p-5">
                    <div className="flex flex-wrap gap-1.5">
                      {(detail.data.extraction.entities || []).map((e: any, i: number) => {
                        const mono = MASKABLE_ENTITIES.includes(e.entity_type)
                        return (
                          <span key={i} className="inline-flex items-center gap-1.5 rounded-md border border-[var(--color-border)] bg-[var(--color-surface-solid)] px-2 py-1 text-[11.5px]">
                            <span className={`font-semibold text-[var(--color-text)] ${mono ? 'mono-id' : ''}`}>{e.surface}</span>
                            <span className="text-[10px] font-semibold uppercase tracking-wide text-[var(--color-primary)]">
                              {tok(t.tokens.entityType, e.entity_type)}
                            </span>
                          </span>
                        )
                      })}
                    </div>
                    <p className="mt-3 text-[11.5px] text-[var(--color-text-muted)]">
                      {t.evidence.nerBackend}: {detail.data.extraction.backend?.ner_backend} · {detail.data.extraction.backend?.rule_layer}
                    </p>
                    <p className="mt-1 text-[11.5px] leading-relaxed text-[var(--color-text-muted)]">
                      Extracted surfaces are quoted from this document. Structured PHONE / ACCOUNT / DEVICE
                      identifiers are masked wherever they are presented as graph entities; the document text
                      itself stays readable because that is what an investigator has to read.
                    </p>
                  </div>
                </section>
              )}

              {/* chain of custody */}
              <section className="surface-solid">
                <header className="border-b border-[var(--color-border)] px-5 py-3.5">
                  <h2 className="section-header !text-[13px]">{t.evidence.provenance}</h2>
                </header>
                <div className="p-5">
                  <ol className="space-y-3 border-l-2 border-[var(--color-primary-soft)] pl-4">
                    {(ev.provenance || []).map((p: any, i: number) => (
                      <li key={i} className="relative">
                        <span className="absolute -left-[22px] top-1.5 h-2.5 w-2.5 rounded-full border-2 border-[var(--color-surface-solid)] bg-[var(--color-primary)]" />
                        <p className="text-[12.5px] font-semibold text-[var(--color-text)]">{p.step}</p>
                        <p className="text-[11.5px] text-[var(--color-text-muted)]">{fmt.dateTime(p.timestamp)} · {p.actor}</p>
                        <p className="text-[12px] text-[var(--color-text)]">{p.detail}</p>
                      </li>
                    ))}
                  </ol>
                  {(detail.data.ledger || []).length > 0 && (
                    <div className="mt-4">
                      <SectionHeader>{t.evidence.ledgerAnchors}</SectionHeader>
                      <ul className="space-y-1.5">
                        {detail.data.ledger.map((b: any) => (
                          <li key={b.index} className="flex flex-wrap items-center gap-2 rounded-[10px] border border-[var(--color-border)] px-2.5 py-1.5 text-[11.5px]">
                            <Badge tone="navy">#{b.index}</Badge>
                            <span className="font-semibold text-[var(--color-text)]">{tok(t.tokens.eventType, b.event_type)}</span>
                            <span className="text-[var(--color-text-muted)]">{fmt.dateTime(b.timestamp)}</span>
                            <Hash value={b.block_hash} chars={12} />
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </section>
            </>
          )}

          {selected && !detail.loading && !detail.error && (detail.data?.related_relationships || []).length > 0 && (
            <Card solid title={t.analysis.net.graphTitle} icon="network" subtitle={`${detail.data.related_relationships.length} candidate relationship(s) generated from this document`}>
              <ul className="space-y-1.5">
                {detail.data.related_relationships.map((r: any) => (
                  <li key={r.id} className="rounded-[10px] border border-[var(--color-border)] px-3 py-2">
                    <p className="text-[12.5px] font-semibold text-[var(--color-text)]">
                      {r.source_label} → {r.target_label}
                    </p>
                    <div className="mt-1 flex flex-wrap items-center gap-1.5 text-[11.5px] text-[var(--color-text-muted)]">
                      <Badge tone="slate">{tok(t.tokens.relationshipType, r.rel_type)}</Badge>
                      <StatusPill status={r.verification_status} />
                      <span className="mono-id">{r.id}</span>
                    </div>
                  </li>
                ))}
              </ul>
              <p className="mt-3 text-[11.5px] leading-relaxed text-[var(--color-text-muted)]">
                These are analytical candidates, not confirmed facts. A link becomes VERIFIED only after a
                supervisor records a decision; nothing is merged automatically.
              </p>
            </Card>
          )}
        </div>
      </div>

      <UploadModal open={uploadOpen} onClose={() => setUploadOpen(false)} defaultCase={caseFilter || cases[0]?.case_id || ''}
        onDone={() => { setUploadOpen(false); list.reload() }} />
    </>
  )
}

function UploadModal({ open, onClose, defaultCase, onDone }: { open: boolean; onClose: () => void; defaultCase: string; onDone: () => void }) {
  const { t, tok } = useI18n()
  const { cases, notify } = useApp()
  const [mode, setMode] = useState<'sample' | 'text' | 'file'>('sample')
  const [caseId, setCaseId] = useState(defaultCase)
  const [type, setType] = useState('FIR')
  const [source, setSource] = useState('Police Report')
  const [declaredTrust, setDeclaredTrust] = useState('OFFICER_UPLOAD')
  const [text, setText] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => { setCaseId(defaultCase) }, [defaultCase])

  async function submit() {
    setErr(null)
    if (!caseId) { setErr('Select the case this evidence belongs to.'); return }
    if (mode === 'text' && text.trim().length < 20) { setErr('Provide at least 20 characters of evidence text.'); return }
    if (mode === 'file' && !file) { setErr('Choose a file to upload.'); return }
    setBusy(true)
    try {
      let created: any
      if (mode === 'file' && file) {
        const form = new FormData()
        form.append('case_id', caseId); form.append('evidence_type', type)
        form.append('source', source || file.name); form.append('notes', 'Uploaded via evidence workspace')
        form.append('source_trust', declaredTrust)
        form.append('file', file)
        created = await api.upload<any>('/api/evidence/upload', form)
      } else {
        created = await api.post<any>('/api/evidence', {
          case_id: caseId, evidence_type: type, source,
          text_content: mode === 'text' ? text : undefined,
          use_synthetic_sample: mode === 'sample',
          source_trust: declaredTrust,
        })
      }
      notify('success', `Evidence ${created.evidence_id} registered`, 'SHA-256 computed and anchored to the ledger.')
      try {
        await api.post(`/api/evidence/${created.evidence_id}/process`, {})
        notify('info', t.evidence.processedToast(created.evidence_id), t.evidence.processedToastBody)
      } catch { /* processing permission may be absent; registration still succeeded */ }
      onDone()
    } catch (error) {
      setErr(error instanceof ApiError ? error.message : t.evidence.registerFailed)
    } finally { setBusy(false) }
  }

  return (
    <Modal open={open} onClose={onClose} title={t.evidence.registerTitle}
      subtitle={t.evidence.registerSubtitle}
      footer={
        <>
          <Button size="sm" onClick={onClose}>{t.evidence.cancel}</Button>
          <Button size="sm" variant="primary" icon="upload" loading={busy} onClick={submit}>{t.evidence.registerAndProcess}</Button>
        </>
      }>
      <div className="space-y-4">
        <div className="flex flex-wrap gap-2">
          {(['sample', 'text', 'file'] as const).map((m) => (
            <button key={m} onClick={() => setMode(m)} aria-pressed={mode === m}
              className={`focus-ring rounded-[10px] px-3 py-1.5 text-[12.5px] font-semibold transition ${
                mode === m
                  ? 'bg-[var(--color-primary)] text-white'
                  : 'border border-[var(--color-border)] bg-[var(--color-surface-solid)] text-[var(--color-text)] hover:border-[var(--color-primary)]'
              }`}>
              {m === 'sample' ? t.evidence.modeSample : m === 'text' ? t.evidence.modeText : t.evidence.modeFile}
            </button>
          ))}
        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <Field label={t.evidence.fieldCase} required>
            <Select value={caseId} onChange={(e) => setCaseId(e.target.value)}>
              <option value="">{t.evidence.selectCase}</option>
              {cases.map((c) => <option key={c.case_id} value={c.case_id}>{c.case_id} — {c.title}</option>)}
            </Select>
          </Field>
          <Field label={t.evidence.fieldEvidenceType} required>
            <Select value={type} onChange={(e) => setType(e.target.value)}>
              {TYPES.map((et) => <option key={et} value={et}>{tok(t.tokens.evidenceType, et)}</option>)}
            </Select>
          </Field>
          <Field label={t.evidence.fieldSource}>
            <TextInput value={source} onChange={(e) => setSource(e.target.value)} placeholder={t.evidence.fieldSourcePlaceholder} />
          </Field>
          <Field label="Source trust (declared provenance)"
            hint="Weights how much this document can corroborate on its own: officer 1.00 · bulk 0.60 · external 0.35.">
            <Select value={declaredTrust} onChange={(e) => setDeclaredTrust(e.target.value)}>
              <option value="OFFICER_UPLOAD">OFFICER_UPLOAD (1.00)</option>
              <option value="BULK_IMPORT">BULK_IMPORT (0.60)</option>
              <option value="EXTERNAL_SUBMISSION">EXTERNAL_SUBMISSION (0.35)</option>
            </Select>
          </Field>
        </div>

        {mode === 'text' && (
          <Field label={t.evidence.fieldText} hint={t.evidence.fieldTextHint}>
            <TextArea value={text} onChange={(e) => setText(e.target.value)} className="min-h-[130px]"
              placeholder={t.evidence.fieldTextPlaceholder} />
          </Field>
        )}

        {mode === 'file' && (
          <Field label={t.evidence.fieldFile} hint={t.evidence.fieldFileHint}>
            <input type="file" onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="focus-ring w-full rounded-[10px] border border-[var(--color-border)] bg-[var(--color-surface-solid)] px-3 py-2 text-[13px] file:mr-3 file:rounded-md file:border-0 file:bg-[var(--color-primary)] file:px-3 file:py-1.5 file:text-[12px] file:font-semibold file:text-white" />
          </Field>
        )}

        {mode === 'sample' && (
          <p className="rounded-[12px] border border-[var(--color-primary)] bg-[var(--color-primary-soft)] px-3 py-2 text-[12.5px] text-[var(--color-text)]">
            {t.evidence.sampleNoteA} <span className="font-semibold">{tok(t.tokens.evidenceType, type)}</span> {t.evidence.sampleNoteB}
          </p>
        )}

        <p className="rounded-[12px] border border-dashed border-[var(--color-text-muted)] px-3 py-2 text-[12px] leading-relaxed text-[var(--color-text-muted)]">
          Registration is immutable: the SHA-256 is computed on upload and the record is anchored to the
          permissioned ledger. Rejecting an item later changes its verification status — the original finding
          and its hash are never deleted.
        </p>

        {err && (
          <p className="rounded-[12px] border border-[var(--color-danger)] bg-[rgba(196,52,31,0.06)] px-3 py-2 text-[12.5px] text-[var(--color-danger)]">{err}</p>
        )}
      </div>
    </Modal>
  )
}
```

