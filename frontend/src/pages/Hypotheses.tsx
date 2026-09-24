import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApp } from '../state/AppContext'
import { usePost } from '../hooks/useFetch'
import { api, ApiError } from '../services/api'
import { Icon } from '../components/shared/Icon'
import {
  Badge, Button, Card, EmptyState, ErrorState, Field, InsufficientEvidence, LoadingBlock, Modal, PageHeader,
  Select, SupportBadge, StatusBadge, TextArea,
} from '../components/shared/ui'
import { useI18n } from '../i18n/LanguageContext'

const STATUS_TONE: Record<string, any> = {
  'CORROBORATED ANALYTICAL LEAD': 'green',
  'PARTIALLY CORROBORATED - FURTHER EVIDENCE REQUIRED': 'amber',
  'CONTRADICTORY EVIDENCE': 'red',
  'INSUFFICIENT EVIDENCE': 'slate',
}

export default function Hypotheses() {
  const { t } = useI18n()
  const { cases, can, notify } = useApp()
  const navigate = useNavigate()
  const [caseId, setCaseId] = useState('')
  const [decision, setDecision] = useState<{ set: any; hyp: any; kind: 'verify' | 'reject' } | null>(null)
  const [rationale, setRationale] = useState('')
  const [busy, setBusy] = useState(false)
  const [decided, setDecided] = useState<Record<string, string>>({})

  const body = useMemo(() => ({ case_ids: caseId ? [caseId] : [] }), [caseId])
  const { data, loading, error, reload } = usePost<any>('/api/analysis/hypotheses', body, [])

  async function submitDecision() {
    if (!decision) return
    const key = `${decision.set.hypothesis_set_id}::${decision.hyp.hypothesis_id}`
    setBusy(true)
    try {
      await api.post(`/api/findings/${encodeURIComponent(key)}/${decision.kind}`, {
        object_type: 'HYPOTHESIS',
        case_id: decision.set.case_ids?.[0] || null,
        rationale: rationale.trim() || (decision.kind === 'verify'
          ? 'Hypothesis accepted as the current working analytical explanation.'
          : 'Hypothesis discounted against the cited evidence.'),
        evidence_ids: decision.hyp.supporting_evidence || [],
      })
      setDecided((d) => ({ ...d, [key]: decision.kind === 'verify' ? 'HUMAN_VERIFIED' : 'REJECTED' }))
      notify('success', decision.kind === 'verify' ? 'Hypothesis accepted' : 'Hypothesis discounted',
        'Competing hypotheses are retained; nothing is deleted.')
      setDecision(null); setRationale('')
    } catch (err) {
      notify('error', 'Decision failed', err instanceof ApiError ? err.message : undefined)
    } finally { setBusy(false) }
  }

  return (
    <>
      <PageHeader
        tagline={t.pages.hypotheses.tagline}
        title={t.pages.hypotheses.title}
        description={t.pages.hypotheses.description}
      >
        <Button icon="refresh" onClick={reload}>{t.reasoning.hyp.regenerate}</Button>
        <Button icon="gaps" onClick={() => navigate('/information-gaps')}>{t.reasoning.hyp.openGaps}</Button>
      </PageHeader>

      <Card solid title={t.reasoning.hyp.scope} icon="filter" className="mb-4"
        subtitle={data ? `${data.hypothesis_sets?.length || 0} observation(s) with competing hypotheses` : ''}>
        <Select value={caseId} onChange={(e) => setCaseId(e.target.value)} className="md:max-w-md">
          <option value="">{t.reasoning.hyp.allCasesRecommended}</option>
          {cases.map((c) => <option key={c.case_id} value={c.case_id}>{c.case_id} — {c.title}</option>)}
        </Select>
      </Card>

      {loading && <LoadingBlock label={t.reasoning.hyp.generating} rows={4} />}
      {error && <ErrorState message={error} onRetry={reload} />}
      {data && !data.sufficient && (
        <InsufficientEvidence message={data.message}
          gap="No observation in this scope has enough supporting records to generate competing explanations." />
      )}

      <div className="space-y-4">
        {data && (data.hypothesis_sets?.length ?? 0) === 0 && (
          <EmptyState
            title={t.common.noData}
            message={t.reasoning.hyp.none}
            icon="hypotheses"
          />
        )}
        {data?.hypothesis_sets?.map((set: any) => (
          <Card solid key={set.hypothesis_set_id} title={set.observation} icon="hypotheses"
            subtitle={`${set.hypothesis_set_id} · cases ${set.case_ids.join(', ')}`}
            actions={<Badge tone={STATUS_TONE[set.status] || 'slate'}>{set.status}</Badge>}>
            <div className="space-y-3">
              {set.hypotheses.map((h: any) => {
                const key = `${set.hypothesis_set_id}::${h.hypothesis_id}`
                const status = decided[key]
                return (
                  <div key={h.hypothesis_id}
                    className={`rounded-xl border px-4 py-3 ${h.rank === 1 ? 'border-[var(--color-primary)] bg-[var(--color-primary-soft)]/45' : 'border-[var(--color-border)] bg-[var(--color-surface-solid)]'}`}>
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <div className="flex items-start gap-2">
                        <span className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-lg text-[11.5px] font-bold ${
                          h.rank === 1 ? 'bg-[var(--color-primary)] text-white' : 'bg-white text-[var(--color-text)] ring-1 ring-[rgba(147,194,251,0.6)]'}`}>
                          {h.rank}
                        </span>
                        <div>
                          <p className="text-[13.5px] font-semibold text-[var(--color-primary-deep)]">{h.statement}</p>
                          <p className="text-[11px] text-[var(--color-text-muted)]/70">{h.hypothesis_id}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <SupportBadge level={h.support_level} />
                        {status && <StatusBadge status={status} />}
                      </div>
                    </div>

                    <div className="mt-2 flex items-center gap-2">
                      <div className="h-2 flex-1 overflow-hidden rounded-full bg-[var(--color-primary-soft)]">
                        <div className="h-full rounded-full bg-[var(--color-primary)]"
                          style={{ width: `${Math.min(100, Math.round(h.support_score * 100))}%` }} />
                      </div>
                      <span className="w-24 text-right text-[11.5px] font-bold text-[var(--color-primary-deep)]">support {h.support_score}</span>
                    </div>

                    <div className="mt-2.5 grid grid-cols-1 gap-2.5 md:grid-cols-3">
                      <EvidenceColumn title={t.reasoning.hyp.supporting} tone="green" items={h.supporting_evidence}
                        onOpen={(id) => navigate(`/evidence?focus=${id}`)} />
                      <EvidenceColumn title={t.reasoning.hyp.contradicting} tone="red" items={h.contradicting_evidence}
                        onOpen={(id) => navigate(`/evidence?focus=${id}`)} />
                      <div>
                        <p className="text-[11px] font-bold uppercase tracking-wider text-[var(--color-text-muted)]/60">{t.reasoning.hyp.missing}</p>
                        <ul className="mt-1 space-y-1">
                          {(h.missing_information || []).length === 0 && <li className="text-[12px] text-[var(--color-text-muted)]/75">{t.reasoning.hyp.noneRecorded}</li>}
                          {(h.missing_information || []).map((m: string, i: number) => (
                            <li key={i} className="flex items-start gap-1.5 text-[12px] text-[var(--color-text)]">
                              <span className="mt-0.5 text-amber-600"><Icon name="gaps" size={12} /></span>{m}
                            </li>
                          ))}
                        </ul>
                      </div>
                    </div>

                    {h.supporting_signals?.length > 0 && (
                      <p className="mt-2 text-[11.5px] text-[var(--color-text-muted)]/85">
                        <span className="font-semibold text-[var(--color-text)]">{t.reasoning.hyp.signals}:</span> {h.supporting_signals.join(' · ')}
                      </p>
                    )}

                    {can('verification:decide') && !status && (
                      <div className="mt-2.5 flex flex-wrap gap-2">
                        <Button size="sm" variant="success" icon="check"
                          onClick={() => { setDecision({ set, hyp: h, kind: 'verify' }); setRationale('') }}>
                          Accept as working hypothesis
                        </Button>
                        <Button size="sm" variant="danger" icon="reject"
                          onClick={() => { setDecision({ set, hyp: h, kind: 'reject' }); setRationale('') }}>
                          Discount
                        </Button>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>

            <div className="mt-3 space-y-1.5">
              <p className="rounded-lg border border-[var(--color-primary-deep)]/10 bg-[var(--color-primary-deep)]/[0.04] px-3 py-2 text-[11.5px] text-[var(--color-text)]">
                <span className="font-semibold">{t.reasoning.hyp.rankingMethod}:</span> {set.ranking_method}
              </p>
              <p className="rounded-[10px] border border-[var(--color-warning)] px-3 py-2 text-[11.5px] text-[var(--color-warning)]">{set.note}</p>
            </div>

            <div className="mt-2.5 flex flex-wrap gap-2">
              <Button size="sm" icon="network" onClick={() => navigate('/network')}>{t.reasoning.hyp.inspectNetwork}</Button>
              <Button size="sm" icon="timeline" onClick={() => navigate('/timeline')}>{t.reasoning.hyp.inspectTimeline}</Button>
              <Button size="sm" icon="nextbest" onClick={() => navigate('/next-best-action')}>{t.reasoning.hyp.nextBestAction}</Button>
            </div>
          </Card>
        ))}
      </div>

      <Modal open={Boolean(decision)} onClose={() => setDecision(null)}
        title={decision?.kind === 'verify' ? 'Accept working hypothesis' : 'Discount hypothesis'}
        subtitle={decision?.hyp.statement}
        footer={
          <>
            <Button onClick={() => setDecision(null)}>{t.reasoning.hyp.cancel}</Button>
            <Button variant={decision?.kind === 'verify' ? 'success' : 'danger'} loading={busy}
              icon={decision?.kind === 'verify' ? 'check' : 'reject'} onClick={submitDecision}>{t.reasoning.hyp.recordDecision}</Button>
          </>
        }>
        <p className="mb-2 text-[12.5px] text-[var(--color-text)]">
          A working hypothesis is an analytical position, not a finding of fact or guilt. Competing hypotheses
          remain visible after your decision so the reasoning stays auditable.
        </p>
        <Field label={t.reasoning.hyp.rationale} hint={t.reasoning.hyp.rationaleHint}>
          <TextArea value={rationale} onChange={(e) => setRationale(e.target.value)}
            placeholder={t.reasoning.hyp.rationalePlaceholder} />
        </Field>
      </Modal>
    </>
  )
}

function EvidenceColumn({ title, tone, items, onOpen }: {
  title: string; tone: 'green' | 'red'; items?: string[]; onOpen: (id: string) => void
}) {
  const { t } = useI18n()
  const cls = tone === 'green'
    ? 'bg-[rgba(30,142,90,0.07)] text-[var(--color-success)] ring-[var(--color-success)] hover:bg-[rgba(30,142,90,0.10)]'
    : 'bg-rose-50 text-[var(--color-danger)] ring-[var(--color-danger)] hover:bg-[rgba(196,52,31,0.10)]'
  return (
    <div>
      <p className="text-[11px] font-bold uppercase tracking-wider text-[var(--color-text-muted)]/60">{title}</p>
      <div className="mt-1 flex flex-wrap gap-1.5">
        {(items || []).length === 0 && <span className="text-[12px] text-[var(--color-text-muted)]/75">{t.reasoning.hyp.none}</span>}
        {(items || []).map((id) => (
          <button key={id} onClick={() => onOpen(id)}
            className={`focus-ring rounded-md px-2 py-1 font-mono text-[11px] font-semibold ring-1 ${cls}`}>
            {id}
          </button>
        ))}
      </div>
    </div>
  )
}
