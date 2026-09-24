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
