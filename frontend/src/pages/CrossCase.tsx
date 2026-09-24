import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApp } from '../state/AppContext'
import { usePost, useFetch } from '../hooks/useFetch'
import { api, ApiError } from '../services/api'
import AgentRunModal from '../components/agents/AgentRunModal'
import { Icon } from '../components/shared/Icon'
import {
  Badge, Button, Card, EmptyState, ErrorState, InsufficientEvidence, LoadingBlock, PageHeader,
  SignalRow, SupportBadge, StatusBadge, TextArea, Modal, Field,
} from '../components/shared/ui'
import { useI18n } from '../i18n/LanguageContext'

export default function CrossCase() {
  const { t, tok } = useI18n()
  const { cases, can, notify } = useApp()
  const navigate = useNavigate()
  const [scope, setScope] = useState<string[]>([])
  const [agentOpen, setAgentOpen] = useState(false)
  const [decision, setDecision] = useState<{ link: any; kind: 'verify' | 'reject' } | null>(null)
  const [rationale, setRationale] = useState('')
  const [busy, setBusy] = useState(false)
  const [decided, setDecided] = useState<Record<string, string>>({})

  const body = useMemo(() => ({ case_ids: scope }), [scope])
  const { data, loading, error, reload } = usePost<any>('/api/analysis/cross-case', body, [])
  const contradictions = useFetch<any>('/api/contradictions', [])

  function toggleCase(id: string) {
    setScope((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]))
  }

  async function submitDecision() {
    if (!decision) return
    setBusy(true)
    try {
      await api.post(`/api/findings/${encodeURIComponent(decision.link.link_id)}/${decision.kind}`, {
        object_type: 'CROSS_CASE_LINK',
        case_id: decision.link.case_a,
        rationale: rationale.trim() || (decision.kind === 'verify'
          ? 'Cross-case association reviewed against the cited evidence and accepted as an investigative lead.'
          : 'Cross-case association not supported by the cited evidence.'),
        evidence_ids: decision.link.evidence_ids,
      })
      setDecided((d) => ({ ...d, [decision.link.link_id]: decision.kind === 'verify' ? 'HUMAN_VERIFIED' : 'REJECTED' }))
      notify('success', `Association ${decision.kind === 'verify' ? 'verified' : 'rejected'}`,
        'Decision written to the audit trail. Original analytical output is preserved.')
      setDecision(null); setRationale('')
    } catch (err) {
      notify('error', 'Decision failed', err instanceof ApiError ? err.message : undefined)
    } finally { setBusy(false) }
  }

  return (
    <>
      <PageHeader
        tagline={t.pages.crossCase.tagline}
        title={t.pages.crossCase.title}
        description={t.pages.crossCase.description}
      >
        <Button icon="refresh" onClick={reload}>{t.analysis.xc.rerun}</Button>
        {can('analysis:run') && (
          <Button variant="primary" icon="spark" onClick={() => setAgentOpen(true)}>{t.analysis.xc.runAgentPlan}</Button>
        )}
      </PageHeader>

      <Card solid title={t.analysis.xc.caseScope} icon="cases" className="mb-4"
        subtitle={scope.length ? t.analysis.xc.casesSelected(scope.length) : t.analysis.er.allAuthorizedCases}>
        <div className="flex flex-wrap gap-1.5">
          <button onClick={() => setScope([])}
            className={`focus-ring rounded-md px-2.5 py-1.5 text-[11.5px] font-semibold transition ${
              scope.length === 0 ? 'bg-[var(--color-primary)] text-white' : 'bg-[var(--color-surface-solid)] text-[var(--color-text)] ring-1 ring-[var(--color-border)]'}`}>
            {t.analysis.xc.allAuthorized}
          </button>
          {cases.map((c) => (
            <button key={c.case_id} onClick={() => toggleCase(c.case_id)}
              className={`focus-ring rounded-md px-2.5 py-1.5 text-[11.5px] font-semibold transition ${
                scope.includes(c.case_id) ? 'bg-[var(--color-primary)] text-white' : 'bg-[var(--color-surface-solid)] text-[var(--color-text)] ring-1 ring-[var(--color-border)] hover:bg-[var(--color-primary-soft)]'}`}>
              {c.case_id}
            </button>
          ))}
        </div>
        {data?.algorithm && (
          <p className="mt-2.5 text-[11.5px] text-[var(--color-text-muted)]/75"><span className="font-semibold">{t.analysis.xc.algorithm}:</span> {data.algorithm}</p>
        )}
      </Card>

      {loading && <LoadingBlock label={t.analysis.xc.correlating} rows={4} />}
      {error && <ErrorState message={error} onRetry={reload} />}
      {data && !data.sufficient && <InsufficientEvidence message={data.message}
        gap={t.analysis.xc.insufficientGap} />}

      {data?.sufficient && (
        <div className="space-y-4">
          {data.associations.length === 0 && (
            <EmptyState
              title={t.common.noResults}
              message={t.common.noRecords}
              icon="crosscase"
              hint={t.analysis.xc.insufficientGap}
            />
          )}
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            {data.associations.map((a: any) => {
              const status = decided[a.link_id] || a.verification_status
              return (
                <Card solid key={a.link_id} title={`${a.case_a} ↔ ${a.case_b}`} icon="crosscase"
                  subtitle={`${a.case_a_title} · ${a.case_b_title}`}
                  actions={<div className="flex items-center gap-1.5"><SupportBadge level={a.support_level} /><Badge tone="blue">{a.strength}</Badge></div>}>
                  <div className="mb-2 flex flex-wrap items-center gap-1.5">
                    <Badge tone="amber">{tok(t.tokens.leadStatus, a.status)}</Badge>
                    <StatusBadge status={status} />
                  </div>

                  <p className="text-[11px] font-bold uppercase tracking-wider text-[var(--color-text-muted)]/60">{t.analysis.xc.why}</p>
                  <ul className="mt-1 space-y-1">
                    {a.why_connected.map((w: string, i: number) => (
                      <li key={i} className="flex items-start gap-1.5 text-[12.5px] text-[var(--color-text)]">
                        <span className="mt-0.5 text-[var(--color-primary)]"><Icon name="link" size={12} /></span>{w}
                      </li>
                    ))}
                  </ul>

                  <p className="mt-2.5 text-[11px] font-bold uppercase tracking-wider text-[var(--color-text-muted)]/60">{t.analysis.xc.signals}</p>
                  <ul className="mt-1">{a.signals.map((s: any, i: number) => <SignalRow key={i} signal={s} />)}</ul>

                  {a.entity_pairs?.length > 0 && (
                    <>
                      <p className="mt-2.5 text-[11px] font-bold uppercase tracking-wider text-[var(--color-text-muted)]/60">{t.analysis.xc.bridging}</p>
                      <div className="mt-1 flex flex-wrap gap-1.5">
                        {a.entity_pairs.map((p: any, i: number) => (
                          <button key={i} onClick={() => navigate(`/entities?focus=${p.entity_id || p.left || ''}`)}
                            className="focus-ring rounded-md bg-[var(--color-primary-soft)] px-2 py-1 text-[11px] font-semibold text-[var(--color-text)] ring-1 ring-[var(--color-primary)] hover:bg-[var(--color-primary-soft)]">
                            {p.label || `${p.left} ↔ ${p.right}`}{p.match_type ? ` · ${p.match_type}` : ''}
                          </button>
                        ))}
                      </div>
                    </>
                  )}

                  <p className="mt-2.5 text-[11px] font-bold uppercase tracking-wider text-[var(--color-text-muted)]/60">{t.analysis.xc.evidence}</p>
                  <div className="mt-1 flex flex-wrap gap-1.5">
                    {a.evidence_ids.map((e: string) => (
                      <button key={e} onClick={() => navigate(`/evidence?focus=${e}`)}
                        className="focus-ring rounded-md bg-[var(--color-surface-solid)] px-2 py-1 font-mono text-[11px] text-[var(--color-text)] ring-1 ring-[var(--color-border)] hover:bg-[var(--color-primary-soft)]">
                        {e}
                      </button>
                    ))}
                  </div>

                  <p className="mt-2.5 rounded-[10px] border border-[var(--color-warning)] px-2.5 py-1.5 text-[11.5px] text-[var(--color-warning)]">{a.disclaimer}</p>

                  <div className="mt-2.5 flex flex-wrap gap-2">
                    <Button size="sm" icon="network" onClick={() => navigate('/network')}>{t.analysis.xc.viewInGraph}</Button>
                    <Button size="sm" icon="timeline" onClick={() => navigate('/timeline')}>{t.analysis.xc.timeline}</Button>
                    {can('verification:decide') && status === 'UNVERIFIED' && (
                      <>
                        <Button size="sm" variant="success" icon="check" onClick={() => { setDecision({ link: a, kind: 'verify' }); setRationale('') }}>{t.analysis.xc.verify}</Button>
                        <Button size="sm" variant="danger" icon="reject" onClick={() => { setDecision({ link: a, kind: 'reject' }); setRationale('') }}>{t.analysis.xc.reject}</Button>
                      </>
                    )}
                  </div>
                </Card>
              )
            })}
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-[1.4fr_1fr]">
            <Card solid title={t.analysis.xc.multiCaseEntities} icon="entities"
              subtitle={t.analysis.xc.sharedEntityRecords(data.entity_overlap.length)}>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-[12.5px]">
                  <thead>
                    <tr className="border-b border-[rgba(147,194,251,0.5)] text-[11px] uppercase tracking-wider text-[var(--color-text-muted)]/60">
                      <th className="py-1.5 pr-3">{t.analysis.xc.thEntity}</th><th className="py-1.5 pr-3">{t.analysis.xc.thType}</th>
                      <th className="py-1.5 pr-3">{t.analysis.xc.thCases}</th><th className="py-1.5 pr-3">{t.analysis.xc.thEvidence}</th><th className="py-1.5">{t.analysis.xc.thStatus}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.entity_overlap.map((e: any) => (
                      <tr key={e.entity_id} className="border-b border-[rgba(147,194,251,0.28)] last:border-0 hover:bg-[var(--color-primary-soft)]/50">
                        <td className="py-1.5 pr-3">
                          <button className="focus-ring font-semibold text-[var(--color-primary-deep)] underline-offset-2 hover:text-[var(--color-primary)] hover:underline"
                            onClick={() => navigate(`/entities?focus=${e.entity_id}`)}>{e.label}</button>
                        </td>
                        <td className="py-1.5 pr-3 text-[var(--color-text-muted)]/85">{tok(t.tokens.entityType, e.entity_type)}</td>
                        <td className="py-1.5 pr-3 font-mono text-[11.5px] text-[var(--color-text)]">{e.cases.join(', ')}</td>
                        <td className="py-1.5 pr-3 font-mono text-[11px] text-[var(--color-text-muted)]/80">{e.evidence_ids.join(', ') || '—'}</td>
                        <td className="py-1.5"><StatusBadge status={e.verification_status} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>

            <Card solid title={t.analysis.xc.contradictions} icon="alert" subtitle={t.analysis.xc.contradictionsSub}>
              {(contradictions.data?.contradictions || []).length === 0 && (
                <p className="text-[13px] text-[var(--color-text-muted)]/80">{t.analysis.xc.noContradictions}</p>
              )}
              {(contradictions.data?.contradictions || []).map((c: any) => (
                <div key={c.contradiction_id} className="mb-2 rounded-xl border border-[var(--color-danger)] bg-[rgba(196,52,31,0.06)] px-3.5 py-2.5">
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-[12.5px] font-bold text-[var(--color-primary-deep)]">{c.contradiction_id} · {c.case_id}</p>
                    <Badge tone="red">{c.status}</Badge>
                  </div>
                  <p className="mt-1 text-[12.5px] text-[var(--color-text)]">{c.statement}</p>
                  <p className="mt-1 text-[11.5px] text-[var(--color-text-muted)]/80"><span className="font-semibold">{t.analysis.xc.impact}:</span> {c.impact}</p>
                  <p className="mt-1 font-mono text-[11px] text-[var(--color-text-muted)]/75">{c.evidence_ids.join(' · ')}</p>
                </div>
              ))}
              {contradictions.data?.policy && (
                <p className="text-[11.5px] italic text-[var(--color-text-muted)]/75">{contradictions.data.policy}</p>
              )}
            </Card>
          </div>
        </div>
      )}

      <Modal open={Boolean(decision)} onClose={() => setDecision(null)}
        title={decision?.kind === 'verify' ? t.analysis.xc.modalVerifyTitle : t.analysis.xc.modalRejectTitle}
        subtitle={decision ? `${decision.link.case_a} ↔ ${decision.link.case_b} · ${decision.link.link_id}` : ''}
        footer={
          <>
            <Button onClick={() => setDecision(null)}>{t.analysis.xc.cancel}</Button>
            <Button variant={decision?.kind === 'verify' ? 'success' : 'danger'} loading={busy}
              icon={decision?.kind === 'verify' ? 'check' : 'reject'} onClick={submitDecision}>
              {decision?.kind === 'verify' ? t.analysis.xc.recordVerification : t.analysis.xc.recordRejection}
            </Button>
          </>
        }>
        <p className="mb-2 text-[12.5px] text-[var(--color-text)]">
          {t.analysis.xc.decisionNote}
        </p>
        <Field label={t.analysis.xc.rationale} hint={t.analysis.xc.rationaleHint}>
          <TextArea value={rationale} onChange={(e) => setRationale(e.target.value)}
            placeholder={t.analysis.xc.rationalePlaceholder} />
        </Field>
      </Modal>

      <AgentRunModal open={agentOpen} onClose={() => setAgentOpen(false)} objective="CROSS_CASE_LINK"
        caseIds={scope} onComplete={() => reload()} />
    </>
  )
}
