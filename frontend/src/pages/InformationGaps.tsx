import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApp } from '../state/AppContext'
import { usePost } from '../hooks/useFetch'
import { api, ApiError } from '../services/api'
import { Icon } from '../components/shared/Icon'
import {
  Badge, Button, Card, EmptyState, ErrorState, InsufficientEvidence, LoadingBlock, Modal, PageHeader, Select, Spinner,
} from '../components/shared/ui'
import { useI18n } from '../i18n/LanguageContext'

const SEVERITY_TONE: Record<string, any> = { HIGH: 'red', MEDIUM: 'amber', LOW: 'slate' }

export default function InformationGaps() {
  const { t, tok } = useI18n()
  const { cases, can, notify } = useApp()
  const navigate = useNavigate()
  const [caseId, setCaseId] = useState('')
  const [severity, setSeverity] = useState('')
  const [result, setResult] = useState<{ title: string; payload: any } | null>(null)
  const [running, setRunning] = useState<string | null>(null)

  const body = useMemo(() => ({ case_ids: caseId ? [caseId] : [] }), [caseId])
  const { data, loading, error, reload } = usePost<any>('/api/analysis/information-gaps', body, [])

  const gaps = (data?.gaps || []).filter((g: any) => !severity || g.severity === severity)

  const gapTypeCounts = useMemo(() => {
    const counts: Record<string, number> = {}
    ;(data?.gaps || []).forEach((g: any) => (g.gap_types || []).forEach((t: string) => { counts[t] = (counts[t] || 0) + 1 }))
    return Object.entries(counts).sort((a, b) => b[1] - a[1])
  }, [data])

  async function runAction(action: any) {
    if (!action?.endpoint) return
    setRunning(action.action_id)
    try {
      const payload = await api.post<any>(action.endpoint, { case_ids: action.case_ids || (caseId ? [caseId] : []) })
      setResult({ title: action.title, payload })
      notify('success', 'Analytical action executed', `${action.title} — result returned by ${payload.agent || 'analysis service'}.`)
      reload()
    } catch (err) {
      notify('error', 'Action failed', err instanceof ApiError ? err.message : undefined)
    } finally { setRunning(null) }
  }

  return (
    <>
      <PageHeader
        tagline={t.pages.gaps.tagline}
        title={t.pages.gaps.title}
        description={t.pages.gaps.description}
      >
        <Button icon="refresh" onClick={reload}>{t.reasoning.gaps.recompute}</Button>
        <Button icon="nextbest" onClick={() => navigate('/next-best-action')}>{t.reasoning.gaps.prioritisedActions}</Button>
      </PageHeader>

      <div className="mb-4 grid grid-cols-1 gap-4 lg:grid-cols-[1fr_1.3fr]">
        <Card solid title={t.reasoning.gaps.scope} icon="filter" subtitle={data ? t.reasoning.gaps.openGapCount(data.gaps?.length || 0) : ''}>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <Select value={caseId} onChange={(e) => setCaseId(e.target.value)}>
              <option value="">{t.reasoning.gaps.allAuthorizedCases}</option>
              {cases.map((c) => <option key={c.case_id} value={c.case_id}>{c.case_id} — {c.title}</option>)}
            </Select>
            <Select value={severity} onChange={(e) => setSeverity(e.target.value)}>
              <option value="">{t.reasoning.gaps.allSeverities}</option>
              {['HIGH', 'MEDIUM', 'LOW'].map((sv) => <option key={sv} value={sv}>{t.reasoning.gaps.severitySuffix(tok(t.tokens.priority, sv))}</option>)}
            </Select>
          </div>
        </Card>
        <Card solid title={t.reasoning.gaps.profile} icon="gaps" subtitle={t.reasoning.gaps.profileSub}>
          {gapTypeCounts.length === 0 && <p className="text-[13px] text-[var(--color-text-muted)]/80">{t.reasoning.gaps.noOpenTypes}</p>}
          <div className="flex flex-wrap gap-2">
            {gapTypeCounts.map(([type, count]) => (
              <span key={type} className="rounded-[10px] border border-[var(--color-warning)] px-2.5 py-1.5 text-[11.5px] font-semibold text-[var(--color-warning)] ring-1 ring-[var(--color-warning)]">
                {t.reasoning.gaps.typeCount(tok(t.tokens.insufficientReason, type), count)}
              </span>
            ))}
          </div>
        </Card>
      </div>

      {loading && <LoadingBlock label={t.reasoning.gaps.comparing} rows={4} />}
      {error && <ErrorState message={error} onRetry={reload} />}
      {data && !data.sufficient && <InsufficientEvidence message={data.message} gap={t.reasoning.gaps.insufficientGap} />}

      <div className="space-y-4">
        {data && gaps.length === 0 && (
          <EmptyState
            title={t.common.noData}
            message={t.reasoning.gaps.noOpenTypes}
            icon="gaps"
          />
        )}
        {gaps.map((g: any) => (
          <Card solid key={g.gap_id} title={g.question} icon="gaps"
            subtitle={t.reasoning.gaps.gapSubtitle(g.gap_id, g.lead_id, g.case_ids.join(', '))}
            actions={
              <div className="flex items-center gap-1.5">
                <Badge tone={SEVERITY_TONE[g.severity] || 'slate'}>{t.reasoning.gaps.severitySuffix(tok(t.tokens.priority, g.severity))}</Badge>
                <Badge tone="slate">{tok(t.tokens.leadStatus, g.status)}</Badge>
              </div>
            }>
            <p className="rounded-lg border border-[var(--color-warning)] bg-[rgba(184,121,26,0.06)] px-3 py-2 text-[12.5px] font-semibold text-[var(--color-warning)]">
              {g.statement}
            </p>
            <p className="mt-2 text-[12.5px] text-[var(--color-text)]"><span className="font-semibold">{t.reasoning.gaps.hypothesisUnderTest}:</span> {g.hypothesis}</p>

            <div className="mt-2.5 grid grid-cols-1 gap-3 lg:grid-cols-2">
              <div className="rounded-xl border border-[var(--color-success)] bg-[rgba(30,142,90,0.07)] px-3.5 py-2.5">
                <p className="text-[11px] font-bold uppercase tracking-wider text-[var(--color-success)]">{t.reasoning.gaps.known}</p>
                <ul className="mt-1 space-y-1">
                  {g.known.map((k: string, i: number) => (
                    <li key={i} className="flex items-start gap-1.5 text-[12.5px] text-[var(--color-text)]">
                      <span className="mt-0.5 text-[var(--color-success)]"><Icon name="check" size={12} /></span>{k}
                    </li>
                  ))}
                </ul>
              </div>
              <div className="rounded-xl border border-[var(--color-danger)] bg-[rgba(196,52,31,0.06)] px-3.5 py-2.5">
                <p className="text-[11px] font-bold uppercase tracking-wider text-[var(--color-danger)]">{t.reasoning.gaps.unknown}</p>
                <ul className="mt-1 space-y-1">
                  {g.unknown.map((u: string, i: number) => (
                    <li key={i} className="flex items-start gap-1.5 text-[12.5px] text-[var(--color-text)]">
                      <span className="mt-0.5 text-rose-500"><Icon name="alert" size={12} /></span>{u}
                    </li>
                  ))}
                </ul>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {(g.gap_types || []).map((gt: string) => (
                    <span key={gt} className="rounded-md bg-[var(--color-surface-solid)] px-2 py-0.5 text-[10.5px] font-bold uppercase tracking-wider text-[var(--color-text-muted)] ring-1 ring-[var(--color-danger)]">{tok(t.tokens.insufficientReason, gt)}</span>
                  ))}
                </div>
              </div>
            </div>

            {g.recommended_action && (
              <div className="mt-3 rounded-xl border border-[var(--color-border)] bg-[var(--color-primary-soft)]/50 px-3.5 py-3">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <p className="text-[11px] font-bold uppercase tracking-wider text-[var(--color-text-muted)]/60">{t.reasoning.gaps.recommendedAction}</p>
                    <p className="text-[13px] font-bold text-[var(--color-primary-deep)]">{g.recommended_action.title}</p>
                    <p className="mt-0.5 text-[12px] text-[var(--color-text)]">{g.recommended_action.rationale}</p>
                    <p className="mt-0.5 font-mono text-[11px] text-[var(--color-text-muted)]/75">
                      {g.recommended_action.method} {g.recommended_action.endpoint} · {t.reasoning.gaps.infoValueSuffix(g.recommended_action.information_value)}
                    </p>
                  </div>
                  {can('analysis:run') && (
                    <Button variant="primary" size="sm" icon="play" loading={running === g.recommended_action.action_id}
                      onClick={() => runAction(g.recommended_action)}>{t.reasoning.gaps.executeAnalysis}</Button>
                  )}
                </div>
              </div>
            )}

            <div className="mt-2.5 flex flex-wrap gap-2">
              <Button size="sm" icon="hypotheses" onClick={() => navigate('/hypotheses')}>{t.reasoning.gaps.relatedHypotheses}</Button>
              <Button size="sm" icon="network" onClick={() => navigate('/network')}>{t.reasoning.gaps.networkView}</Button>
              {g.case_ids?.[0] && <Button size="sm" icon="cases" onClick={() => navigate(`/cases/${g.case_ids[0]}`)}>{t.reasoning.gaps.openCase}</Button>}
            </div>
          </Card>
        ))}
      </div>

      <Modal open={Boolean(result)} onClose={() => setResult(null)} title={t.reasoning.gaps.analysisResult} subtitle={result?.title} width="max-w-3xl">
        {running && <Spinner />}
        {result && <ResultSummary payload={result.payload} />}
      </Modal>
    </>
  )
}

export function ResultSummary({ payload }: { payload: any }) {
  const { t } = useI18n()
  if (!payload) return null
  const K = t.reasoning.gaps.resultKeys
  const entries: Array<[string, string]> = []
  if (payload.agent) entries.push([K.agent, payload.agent])
  if (payload.engine) entries.push([K.engine, payload.engine])
  if (payload.model) entries.push([K.model, payload.model])
  if (payload.algorithm) entries.push([K.algorithm, payload.algorithm])
  if (typeof payload.nodes === 'number') entries.push([K.nodesEdges, `${payload.nodes} / ${payload.edges}`])
  if (payload.associations) entries.push([K.associations, String(payload.associations.length)])
  if (payload.candidate_matches) entries.push([K.candidateMatches, String(payload.candidate_matches.length)])
  if (payload.leads) entries.push([K.leads, String(payload.leads.length)])
  if (payload.gaps) entries.push([K.gaps, String(payload.gaps.length)])
  if (payload.actions) entries.push([K.actions, String(payload.actions.length)])
  if (payload.anomalies) entries.push([K.anomalies, String(payload.anomalies.length)])
  if (payload.event_count) entries.push([K.events, String(payload.event_count)])
  if (payload.summary) entries.push([K.summary, Object.entries(payload.summary).map(([k, v]) => `${k}: ${v}`).join(' · ')])
  if (payload.message) entries.push([K.message, payload.message])

  return (
    <div>
      <dl className="grid grid-cols-1 gap-1.5 sm:grid-cols-2">
        {entries.map(([k, v]) => (
          <div key={k} className="rounded-lg bg-[var(--color-primary-soft)]/70 px-3 py-2">
            <dt className="text-[10.5px] font-bold uppercase tracking-wider text-[var(--color-text-muted)]/60">{k}</dt>
            <dd className="text-[12.5px] font-semibold text-[var(--color-primary-deep)]">{v}</dd>
          </div>
        ))}
      </dl>
      <details className="mt-3">
        <summary className="cursor-pointer text-[12px] font-semibold text-[var(--color-primary)]">{t.reasoning.gaps.showRaw}</summary>
        <pre className="mt-2 max-h-72 overflow-auto rounded-lg bg-[var(--color-primary-deep)]/[0.05] p-3 text-[11px] leading-relaxed text-[var(--color-primary-deep)]">
          {JSON.stringify(payload, null, 2)}
        </pre>
      </details>
    </div>
  )
}
