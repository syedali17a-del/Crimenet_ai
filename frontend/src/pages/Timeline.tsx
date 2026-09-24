import { useMemo, useState } from 'react'
import { useApp } from '../state/AppContext'
import { useFetch } from '../hooks/useFetch'
import { api, ApiError } from '../services/api'
import { Icon } from '../components/shared/Icon'
import {
  Badge, Button, Card, EmptyState, ErrorState, InsufficientEvidence, LoadingBlock, PageHeader, Select,
  SignalRow, TextInput,
} from '../components/shared/ui'
import { useI18n } from '../i18n/LanguageContext'

export default function Timeline() {
  const { t, tok, fmt } = useI18n()
  const { cases, activeCase, can, notify } = useApp()
  const [caseId, setCaseId] = useState(activeCase || '')
  const [entityId, setEntityId] = useState('')
  const [start, setStart] = useState('')
  const [end, setEnd] = useState('')
  const [busy, setBusy] = useState(false)
  const [anomaly, setAnomaly] = useState<any>(null)

  const qs = new URLSearchParams()
  if (caseId) qs.set('case_ids', caseId)
  if (entityId) qs.set('entity_id', entityId)
  if (start) qs.set('start', start)
  if (end) qs.set('end', end)
  const { data, loading, error, reload } = useFetch<any>(`/api/timeline?${qs.toString()}`, [caseId, entityId, start, end])
  const entities = useFetch<any>('/api/entities', [])

  const maxDaily = useMemo(
    () => Math.max(1, ...((data?.daily_activity || []).map((d: any) => d.events) as number[])),
    [data],
  )

  async function runAnomaly() {
    setBusy(true)
    try {
      const res = await api.post<any>('/api/analysis/anomaly', { case_ids: caseId ? [caseId] : [] })
      setAnomaly(res)
      notify(res.sufficient ? 'success' : 'info', 'Anomaly analysis complete',
        res.sufficient ? `${res.anomalies.length} analytical anomaly/anomalies flagged (Isolation Forest)` : res.message)
    } catch (err) {
      notify('error', 'Anomaly analysis failed', err instanceof ApiError ? err.message : undefined)
    } finally { setBusy(false) }
  }

  return (
    <>
      <PageHeader
        tagline={t.pages.timeline.tagline}
        title={t.pages.timeline.title}
        description={t.pages.timeline.description}
      >
        <Button icon="refresh" onClick={reload}>{t.analysis.tl.refresh}</Button>
        {can('analysis:run') && <Button variant="primary" icon="spark" loading={busy} onClick={runAnomaly}>{t.analysis.tl.runAnomaly}</Button>}
      </PageHeader>

      <Card solid title={t.analysis.tl.filters} icon="filter" className="mb-4">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
          <Select value={caseId} onChange={(e) => setCaseId(e.target.value)}>
            <option value="">{t.analysis.tl.allAuthorizedCases}</option>
            {cases.map((c) => <option key={c.case_id} value={c.case_id}>{c.case_id} — {c.title}</option>)}
          </Select>
          <Select value={entityId} onChange={(e) => setEntityId(e.target.value)}>
            <option value="">{t.analysis.tl.allEntities}</option>
            {(entities.data?.entities || []).filter((e: any) => e.entity_type !== 'CASE').map((e: any) => (
              <option key={e.id} value={e.id}>{e.label} ({tok(t.tokens.entityType, e.entity_type)})</option>
            ))}
          </Select>
          <TextInput type="date" value={start} onChange={(e) => setStart(e.target.value)} aria-label={t.analysis.tl.startDate} />
          <TextInput type="date" value={end} onChange={(e) => setEnd(e.target.value)} aria-label={t.analysis.tl.endDate} />
        </div>
      </Card>

      {loading && <LoadingBlock label={t.analysis.tl.analysing} rows={4} />}
      {error && <ErrorState message={error} onRetry={reload} />}

      {data && !data.sufficient && <InsufficientEvidence message={data.message} gap={t.analysis.tl.insufficientGap} />}

      {data?.sufficient && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-[1.5fr_1fr]">
            <Card solid title={t.analysis.tl.distribution} icon="timeline"
              subtitle={t.analysis.tl.distributionSub(data.event_count, data.baseline_events_per_day, fmt.dateShort(data.window.start), fmt.dateShort(data.window.end))}>
              <div className="flex h-40 items-end gap-1.5 overflow-x-auto pb-1">
                {data.daily_activity.map((d: any) => {
                  const spike = data.spikes.some((s: any) => s.date === d.date)
                  return (
                    <div key={d.date} className="flex min-w-[34px] flex-1 flex-col items-center gap-1">
                      <span className="text-[10px] font-bold text-[var(--color-text)]">{d.events}</span>
                      <div
                        title={t.analysis.tl.eventsOnDay(d.date, d.events)}
                        className={`w-full rounded-t-md transition-all ${spike ? 'bg-[var(--color-warning)]' : 'bg-[var(--color-primary)]'}`}
                        style={{ height: `${(d.events / maxDaily) * 100}%`, minHeight: 6 }}
                      />
                      <span className="whitespace-nowrap text-[9.5px] text-[var(--color-text-muted)]/70">{d.date.slice(5)}</span>
                    </div>
                  )
                })}
              </div>
              {data.spikes.length > 0 && (
                <p className="mt-2 rounded-lg border border-[var(--color-warning)] bg-[rgba(184,121,26,0.06)] px-3 py-2 text-[12px] text-[var(--color-text)]">
                  <span className="font-semibold">{t.analysis.tl.spikes}:</span> {data.spikes.map((s: any) => `${s.date} (${s.events})`).join(', ')} — {t.analysis.tl.spikeNote}
                </p>
              )}
            </Card>

            <Card solid title={t.analysis.tl.repeated} icon="refresh" subtitle={t.analysis.tl.repeatedSub}>
              {data.repeated_activity.length === 0 && (
                <EmptyState title={t.common.noData} message={t.analysis.tl.noRepeated} icon="refresh" />
              )}
              <ul className="space-y-1.5">
                {data.repeated_activity.slice(0, 6).map((r: any, i: number) => (
                  <li key={i} className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-solid)] px-3 py-2">
                    <p className="text-[12.5px] font-semibold text-[var(--color-primary-deep)]">{r.entity_id} @ {r.location_id}</p>
                    <p className="text-[11.5px] text-[var(--color-text-muted)]/80">{t.analysis.tl.occurrences(r.occurrences)} · {r.timestamps.map((ts: string) => fmt.dateShort(ts)).join(', ')}</p>
                    <p className="text-[11.5px] text-[var(--color-text-muted)]/70">{t.analysis.tl.evidenceLabel}: {r.evidence_ids.join(', ') || '—'}</p>
                  </li>
                ))}
              </ul>
            </Card>
          </div>

          <Card solid title={t.analysis.tl.convergence} icon="target"
            subtitle={t.analysis.tl.convergenceSub}>
            {data.convergence.length === 0 ? (
              <p className="text-[13px] text-[var(--color-text-muted)]/80">{t.analysis.tl.noConvergence}</p>
            ) : (
              <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
                {data.convergence.map((c: any, i: number) => (
                  <ConvergenceCard key={i} c={c} />
                ))}
              </div>
            )}
          </Card>

          {anomaly && (
            <Card solid title={t.analysis.tl.anomaly} icon="alert"
              subtitle={`${anomaly.model}${anomaly.parameters ? ` · contamination ${anomaly.parameters.contamination}` : ''}`}>
              {!anomaly.sufficient && <InsufficientEvidence message={anomaly.message} />}
              {anomaly.anomalies?.map((a: any, i: number) => (
                <div key={i} className="mb-2 rounded-[12px] border border-[var(--color-warning)] bg-[rgba(184,121,26,0.06)] px-4 py-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="text-[13.5px] font-bold text-[var(--color-primary-deep)]">{t.analysis.tl.accountLabel} {a.account_id} · {a.case_id}</p>
                    <Badge tone="amber">{a.label}</Badge>
                  </div>
                  <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-3">
                    <Metric label={t.analysis.tl.baseline} value={t.analysis.tl.perDay(a.baseline.mean_transactions_per_day)} />
                    <Metric label={t.analysis.tl.observed} value={t.analysis.tl.inOneHour(a.observed.transactions_in_hour)} tone="amber" />
                    <Metric label={t.analysis.tl.anomalyScore} value={a.anomaly_score} />
                  </div>
                  <p className="mt-2 text-[12px] text-[var(--color-text)]">{a.interpretation}</p>
                  <p className="mt-1 text-[11.5px] text-[var(--color-text-muted)]/75">{t.analysis.tl.windowLabel} {a.window} · {t.analysis.tl.evidenceLabel} {a.evidence_ids.join(', ')}</p>
                </div>
              ))}
              {anomaly.safety_note && <p className="text-[11.5px] italic text-[var(--color-text-muted)]/80">{anomaly.safety_note}</p>}
            </Card>
          )}

          <Card solid title={t.analysis.tl.chronological(data.events.length)} icon="clock">
            <ol className="space-y-2.5 border-l-2 border-[var(--color-border)] pl-4">
              {data.events.map((e: any) => (
                <li key={e.event_id} className="relative">
                  <span className="absolute -left-[21px] top-1.5 h-2.5 w-2.5 rounded-full border-2 border-white bg-[var(--color-primary-soft)]0" />
                  <div className="flex flex-wrap items-center gap-1.5">
                    <p className="text-[13px] font-semibold text-[var(--color-primary-deep)]">{e.title}</p>
                    <Badge tone="slate">{tok(t.tokens.eventType, e.event_type)}</Badge>
                    <Badge tone="blue">{e.case_id}</Badge>
                  </div>
                  <p className="text-[11.5px] text-[var(--color-text-muted)]/80">
                    {fmt.dateTime(e.timestamp)}
                    {e.location_label ? ` · ${e.location_label}` : ''} · {t.analysis.tl.evidenceLabel} {e.evidence_id || '—'}
                  </p>
                  {e.entity_labels?.length > 0 && (
                    <p className="mt-0.5 text-[11.5px] text-[var(--color-text-muted)]/70">{t.analysis.tl.entitiesLabel}: {e.entity_labels.join(', ')}</p>
                  )}
                </li>
              ))}
            </ol>
          </Card>

          <p className="rounded-lg border border-[var(--color-primary-deep)]/10 bg-[var(--color-primary-deep)]/[0.04] px-3.5 py-2.5 text-[12px] text-[var(--color-text)]">
            <Icon name="info" size={13} /> {data.safety_note}
          </p>
        </div>
      )}
    </>
  )
}

function ConvergenceCard({ c }: { c: any }) {
  const { can, notify } = useApp()
  const { t, tok, fmt } = useI18n()
  const [decided, setDecided] = useState<string | null>(null)
  const id = `CONV-${c.location_id}-${c.window_start.slice(0, 16)}`

  async function decide(kind: 'verify' | 'reject') {
    try {
      await api.post(`/api/findings/${encodeURIComponent(id)}/${kind}`, {
        object_type: 'CONVERGENCE', case_id: null,
        rationale: kind === 'verify' ? t.analysis.tl.convVerifyRationale : t.analysis.tl.convRejectRationale,
        evidence_ids: c.evidence_ids,
      })
      setDecided(kind === 'verify' ? 'HUMAN_VERIFIED' : 'REJECTED')
      notify('success', kind === 'verify' ? t.analysis.tl.convVerified : t.analysis.tl.convRejected, t.analysis.tl.decisionRecorded)
    } catch (err) {
      notify('error', t.analysis.tl.actionNotPermitted, err instanceof ApiError ? err.message : undefined)
    }
  }

  return (
    <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-solid)] px-4 py-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-[13px] font-bold text-[var(--color-primary-deep)]">{tok(t.tokens.leadStatus, c.status)}</p>
        <Badge tone={decided === 'HUMAN_VERIFIED' ? 'green' : decided === 'REJECTED' ? 'red' : 'amber'}>
          {decided ? tok(t.tokens.verificationStatus, decided) : t.analysis.tl.requiresReview}
        </Badge>
      </div>
      <p className="mt-1 text-[12.5px] text-[var(--color-text)]">
        {c.location_id} · {fmt.dateTime(c.window_start)} → {fmt.time(c.window_end)}
      </p>
      <ul className="mt-1.5">
        {c.signals.map((s: any, i: number) => <SignalRow key={i} signal={s} />)}
      </ul>
      <p className="mt-1.5 text-[11.5px] text-[var(--color-text-muted)]/80">{t.analysis.tl.entitiesLabel}: {c.entities.join(', ')}</p>
      <p className="mt-1 rounded-[10px] border border-[var(--color-warning)] px-2.5 py-1.5 text-[11.5px] text-[var(--color-warning)]">{c.disclaimer}</p>
      {can('verification:decide') && (
        <div className="mt-2 flex gap-2">
          <Button size="sm" variant="success" icon="check" onClick={() => decide('verify')}>{t.analysis.tl.verify}</Button>
          <Button size="sm" variant="danger" icon="reject" onClick={() => decide('reject')}>{t.analysis.tl.reject}</Button>
        </div>
      )}
    </div>
  )
}

function Metric({ label, value, tone = 'blue' }: { label: string; value: React.ReactNode; tone?: 'blue' | 'amber' }) {
  return (
    <div className={`rounded-lg px-3 py-2 ${tone === 'amber' ? 'bg-[rgba(184,121,26,0.10)]' : 'bg-[var(--color-primary-soft)]'}`}>
      <p className="text-[10.5px] font-bold uppercase tracking-wider text-[var(--color-text-muted)]/65">{label}</p>
      <p className="mt-0.5 text-[15px] font-bold text-[var(--color-primary-deep)]">{value}</p>
    </div>
  )
}
