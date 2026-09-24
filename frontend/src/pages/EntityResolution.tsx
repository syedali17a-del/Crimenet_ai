import { useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useApp } from '../state/AppContext'
import { usePost } from '../hooks/useFetch'
import { api, ApiError } from '../services/api'
import EntityPanel from '../components/graph/EntityPanel'
import { Icon } from '../components/shared/Icon'
import {
  Badge, Button, Card, EmptyState, ErrorState, Field, InsufficientEvidence, LoadingBlock, Modal, PageHeader,
  Select, SignalRow, SupportBadge, StatusBadge, TextArea,
} from '../components/shared/ui'
import { useI18n } from '../i18n/LanguageContext'

const MIN_SUPPORT = ['LOW', 'MEDIUM', 'HIGH'] as const

export default function EntityResolution() {
  const { t } = useI18n()
  const { cases, can, notify } = useApp()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const [caseId, setCaseId] = useState('')
  const [minSupport, setMinSupport] = useState<(typeof MIN_SUPPORT)[number]>('LOW')
  const [focus, setFocus] = useState<string | null>(params.get('focus'))
  const [decision, setDecision] = useState<{ match: any; kind: 'verify' | 'reject' } | null>(null)
  const [rationale, setRationale] = useState('')
  const [busy, setBusy] = useState(false)
  const [decided, setDecided] = useState<Record<string, string>>({})

  const body = useMemo(() => ({ case_ids: caseId ? [caseId] : [], min_support: minSupport }), [caseId, minSupport])
  const { data, loading, error, reload } = usePost<any>('/api/analysis/entity-resolution', body, [])

  async function submitDecision() {
    if (!decision) return
    setBusy(true)
    const m = decision.match
    try {
      await api.post(`/api/findings/${encodeURIComponent(m.match_id)}/${decision.kind}`, {
        object_type: 'IDENTITY_MATCH',
        case_id: m.left.cases?.[0] || null,
        rationale: rationale.trim() || (decision.kind === 'verify'
          ? 'Identity match reviewed against shared identifiers and confirmed by the investigator.'
          : 'Identity match not supported; records remain distinct.'),
        evidence_ids: [...(m.left.evidence_ids || []), ...(m.right.evidence_ids || [])],
      })
      setDecided((d) => ({ ...d, [m.match_id]: decision.kind === 'verify' ? 'HUMAN_VERIFIED' : 'REJECTED' }))
      notify('success', decision.kind === 'verify' ? 'Identity match confirmed' : 'Identity match rejected',
        decision.kind === 'verify'
          ? 'Records are linked as the same identity by human decision — no automatic merge occurred.'
          : 'Records remain separate. The original analytical output is preserved.')
      setDecision(null); setRationale('')
    } catch (err) {
      notify('error', 'Decision failed', err instanceof ApiError ? err.message : undefined)
    } finally { setBusy(false) }
  }

  return (
    <>
      <PageHeader
        tagline={t.pages.entities.tagline}
        title={t.pages.entities.title}
        description={t.pages.entities.description}
      >
        <Button icon="refresh" onClick={reload}>{t.analysis.er.rerun}</Button>
      </PageHeader>

      <Card solid title={t.analysis.er.scopeThreshold} icon="filter" className="mb-4"
        subtitle={data ? `${data.compared_records} records compared · ${data.candidate_matches.length} candidate match(es)` : ''}>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <Select value={caseId} onChange={(e) => setCaseId(e.target.value)}>
            <option value="">{t.analysis.er.allAuthorizedCases}</option>
            {cases.map((c) => <option key={c.case_id} value={c.case_id}>{c.case_id} — {c.title}</option>)}
          </Select>
          <Select value={minSupport} onChange={(e) => setMinSupport(e.target.value as any)}>
            {MIN_SUPPORT.map((s) => <option key={s} value={s}>Minimum support: {s}</option>)}
          </Select>
          <div className="flex items-center rounded-lg bg-[rgba(30,142,90,0.07)] px-3 py-2 text-[11.5px] font-semibold text-[var(--color-success)] ring-1 ring-[var(--color-success)]">
            <Icon name="lock" size={13} />
            <span className="ml-1.5">{data?.auto_merge_policy || 'Auto-merge disabled'}</span>
          </div>
        </div>
        {data?.algorithm && <p className="mt-2.5 text-[11.5px] text-[var(--color-text-muted)]/75"><span className="font-semibold">{t.analysis.er.pipeline}:</span> {data.algorithm}</p>}
      </Card>

      {loading && <LoadingBlock label={t.analysis.er.comparing} rows={4} />}
      {error && <ErrorState message={error} onRetry={reload} />}
      {data && !data.sufficient && <InsufficientEvidence message={data.note || 'No comparable identity records in this scope.'} />}

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1fr_340px]">
        <div className="space-y-4">
          {data && (data.candidate_matches?.length ?? 0) === 0 && (
            <EmptyState
              title={t.common.noResults}
              message={t.common.noRecords}
              icon="entities"
              hint={t.analysis.er.allAuthorizedCases}
            />
          )}
          {data?.candidate_matches?.map((m: any) => {
            const status = decided[m.match_id] || m.verification_status
            return (
              <Card solid key={m.match_id} title={`${m.left.label}  ↔  ${m.right.label}`} icon="entities"
                subtitle={m.match_id}
                actions={<div className="flex items-center gap-1.5"><SupportBadge level={m.support_level} /><Badge tone="blue">{m.score}</Badge><StatusBadge status={status} /></div>}>
                <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
                  <RecordCard record={m.left} onOpen={() => setFocus(m.left.entity_id)} />
                  <RecordCard record={m.right} onOpen={() => setFocus(m.right.entity_id)} />
                </div>

                <div className="mt-3 grid grid-cols-1 gap-3 lg:grid-cols-2">
                  <div>
                    <p className="text-[11px] font-bold uppercase tracking-wider text-[var(--color-text-muted)]/60">{t.analysis.er.matchingSignals}</p>
                    <ul className="mt-1">{m.signals.map((s: any, i: number) => <SignalRow key={i} signal={s} />)}</ul>
                    {m.contradictions?.length > 0 && (
                      <div className="mt-2 rounded-lg border border-[var(--color-danger)] bg-[rgba(196,52,31,0.06)] px-3 py-2">
                        <p className="text-[11.5px] font-bold text-[var(--color-danger)]">{t.analysis.er.contradicting}</p>
                        {m.contradictions.map((c: any, i: number) => (
                          <p key={i} className="text-[11.5px] text-[var(--color-text)]">{typeof c === 'string' ? c : c.statement || JSON.stringify(c)}</p>
                        ))}
                      </div>
                    )}
                  </div>
                  <div className="space-y-2">
                    <div>
                      <p className="text-[11px] font-bold uppercase tracking-wider text-[var(--color-text-muted)]/60">{t.analysis.er.fuzzy}</p>
                      <div className="mt-1 grid grid-cols-2 gap-1.5">
                        {Object.entries(m.fuzzy).map(([k, v]) => (
                          <div key={k} className="rounded-md bg-[var(--color-primary-soft)]/80 px-2 py-1">
                            <p className="text-[10px] uppercase tracking-wider text-[var(--color-text-muted)]/60">{k.replace(/_/g, ' ')}</p>
                            <ScoreBar value={Number(v)} />
                          </div>
                        ))}
                      </div>
                    </div>
                    <div>
                      <p className="text-[11px] font-bold uppercase tracking-wider text-[var(--color-text-muted)]/60">{t.analysis.er.tokenComparison}</p>
                      <p className="text-[11.5px] text-[var(--color-text)]">
                        A: {m.tokens.tokens_a.join(' · ')} — B: {m.tokens.tokens_b.join(' · ')}
                      </p>
                      <p className="text-[11.5px] text-[var(--color-text-muted)]/85">
                        Shared: {m.tokens.shared_tokens.join(', ') || 'none'} · initial-compatible: {String(m.tokens.initial_compatible)} · surname match: {String(m.tokens.surname_match)}
                      </p>
                    </div>
                    <div>
                      <p className="text-[11px] font-bold uppercase tracking-wider text-[var(--color-text-muted)]/60">{t.analysis.er.sharedAttributes}</p>
                      <p className="text-[11.5px] text-[var(--color-text)]">
                        {t.analysis.er.lblVehicles}: {m.shared.vehicles.join(', ') || '—'} · {t.analysis.er.lblPhones}: {m.shared.phones.join(', ') || '—'}
                      </p>
                      <p className="text-[11.5px] text-[var(--color-text)]">
                        {t.analysis.er.lblLocations}: {m.shared.locations.join(', ') || '—'} · {t.analysis.er.lblAccounts}: {m.shared.accounts.join(', ') || '—'}
                        {typeof m.temporal_gap_days === 'number' ? ` · temporal gap ${m.temporal_gap_days}d` : ''}
                      </p>
                    </div>
                  </div>
                </div>

                <div className="mt-3 flex flex-wrap items-center justify-between gap-2 rounded-lg border border-[rgba(147,194,251,0.5)] bg-[var(--color-surface-solid)] px-3 py-2">
                  <p className="text-[12.5px] font-semibold text-[var(--color-primary-deep)]">{m.decision}</p>
                  <div className="flex flex-wrap gap-2">
                    <Button size="sm" icon="network" onClick={() => navigate(`/network`)}>{t.analysis.er.compareInGraph}</Button>
                    {can('verification:decide') && status === 'UNVERIFIED' && (
                      <>
                        <Button size="sm" variant="success" icon="check" onClick={() => { setDecision({ match: m, kind: 'verify' }); setRationale('') }}>{t.analysis.er.confirmSame}</Button>
                        <Button size="sm" variant="danger" icon="reject" onClick={() => { setDecision({ match: m, kind: 'reject' }); setRationale('') }}>{t.analysis.er.keepSeparate}</Button>
                      </>
                    )}
                  </div>
                </div>
              </Card>
            )
          })}
        </div>

        <div className="space-y-4 xl:sticky xl:top-[112px] xl:self-start">
          {focus ? (
            <EntityPanel entityId={focus} onClose={() => setFocus(null)} onSelectEntity={setFocus} onChanged={reload} />
          ) : (
            <Card solid title={t.analysis.er.policy} icon="shield">
              <ul className="space-y-2 text-[12.5px] text-[var(--color-text)]">
                {t.analysis.er.policyLines.map((line) => (
                  <li key={line} className="flex items-start gap-1.5"><span className="mt-0.5 text-[var(--color-primary)]"><Icon name="check" size={13} /></span>{line}</li>
                ))}
              </ul>
            </Card>
          )}
        </div>
      </div>

      <Modal open={Boolean(decision)} onClose={() => setDecision(null)}
        title={decision?.kind === 'verify' ? t.analysis.er.modalVerifyTitle : t.analysis.er.modalRejectTitle}
        subtitle={decision ? `${decision.match.left.label} ↔ ${decision.match.right.label} · ${t.analysis.er.modalScore(decision.match.score)}` : ''}
        footer={
          <>
            <Button onClick={() => setDecision(null)}>{t.analysis.er.cancel}</Button>
            <Button variant={decision?.kind === 'verify' ? 'success' : 'danger'} loading={busy}
              icon={decision?.kind === 'verify' ? 'check' : 'reject'} onClick={submitDecision}>
              {t.analysis.er.recordDecision}
            </Button>
          </>
        }>
        <p className="mb-2 text-[12.5px] text-[var(--color-text)]">
          {decision?.kind === 'verify'
            ? t.analysis.er.verifyBody
            : t.analysis.er.rejectBody}
        </p>
        <Field label={t.analysis.er.rationale} hint={t.analysis.er.rationaleHint}>
          <TextArea value={rationale} onChange={(e) => setRationale(e.target.value)}
            placeholder={t.analysis.er.rationalePlaceholder} />
        </Field>
      </Modal>
    </>
  )
}

function RecordCard({ record, onOpen }: { record: any; onOpen: () => void }) {
  const { t } = useI18n()
  return (
    <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-solid)] px-3.5 py-3">
      <div className="flex items-center justify-between gap-2">
        <p className="text-[13.5px] font-bold text-[var(--color-primary-deep)]">{record.label}</p>
        <Badge tone="slate">{record.entity_id}</Badge>
      </div>
      <dl className="mt-1.5 space-y-0.5 text-[11.5px] text-[var(--color-text)]">
        <p><span className="text-[var(--color-text-muted)]/65">{t.analysis.er.lblCases}:</span> {record.cases?.join(', ') || '—'}</p>
        <p><span className="text-[var(--color-text-muted)]/65">{t.analysis.er.lblRole}:</span> {record.role_in_case || record.aliases?.join(', ') || '—'}</p>
        <p><span className="text-[var(--color-text-muted)]/65">{t.analysis.er.lblActivity}:</span> {record.activity_dates?.join(', ') || '—'}</p>
        <p><span className="text-[var(--color-text-muted)]/65">{t.analysis.er.lblVehicles}:</span> {record.vehicles?.join(', ') || '—'}</p>
        <p><span className="text-[var(--color-text-muted)]/65">{t.analysis.er.lblPhones}:</span> {record.phones?.join(', ') || '—'}</p>
        <p><span className="text-[var(--color-text-muted)]/65">{t.analysis.er.lblLocations}:</span> {record.locations?.join(', ') || '—'}</p>
        <p><span className="text-[var(--color-text-muted)]/65">{t.analysis.er.lblEvidence}:</span> {record.evidence_ids?.join(', ') || '—'}</p>
      </dl>
      <Button size="sm" className="mt-2" icon="eye" onClick={onOpen}>{t.analysis.er.openProfile}</Button>
    </div>
  )
}

function ScoreBar({ value }: { value: number }) {
  return (
    <div className="flex items-center gap-1.5">
      <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-[var(--color-primary-soft)]">
        <div className="h-full rounded-full bg-[var(--color-primary)]" style={{ width: `${Math.min(100, value)}%` }} />
      </div>
      <span className="w-9 text-right text-[10.5px] font-bold text-[var(--color-primary-deep)]">{value}</span>
    </div>
  )
}
