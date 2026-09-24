import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApp } from '../state/AppContext'
import { usePost } from '../hooks/useFetch'
import { api, ApiError } from '../services/api'
import { ResultSummary } from './InformationGaps'
import { Icon } from '../components/shared/Icon'
import {
  Badge, Button, Card, EmptyState, ErrorState, InsufficientEvidence, LoadingBlock, Modal, PageHeader, Select,
} from '../components/shared/ui'
import { useI18n } from '../i18n/LanguageContext'

export default function NextBestAction() {
  const { t, tok } = useI18n()
  const { cases, can, notify } = useApp()
  const navigate = useNavigate()
  const [caseId, setCaseId] = useState('')
  const [running, setRunning] = useState<string | null>(null)
  const [result, setResult] = useState<{ title: string; payload: any } | null>(null)
  const [executed, setExecuted] = useState<Record<string, string>>({})

  const body = useMemo(() => ({ case_ids: caseId ? [caseId] : [] }), [caseId])
  const { data, loading, error, reload } = usePost<any>('/api/analysis/next-best-action', body, [])

  async function runAction(action: any) {
    setRunning(action.action_id)
    try {
      const payload = await api.post<any>(action.endpoint, { case_ids: action.case_ids || (caseId ? [caseId] : []) })
      setResult({ title: action.title, payload })
      setExecuted((e) => ({ ...e, [action.action_id]: new Date().toISOString() }))
      notify('success', 'Analytical action executed', `${action.title} completed. Audit entry written.`)
      reload()
    } catch (err) {
      notify('error', 'Action failed', err instanceof ApiError ? err.message : undefined)
    } finally { setRunning(null) }
  }

  const gapProfile = Object.entries(data?.gap_profile || {}) as Array<[string, number]>

  return (
    <>
      <PageHeader
        tagline={t.pages.nextBest.tagline}
        title={t.pages.nextBest.title}
        description={t.pages.nextBest.description}
      >
        <Button icon="refresh" onClick={reload}>{t.reasoning.nba.recompute}</Button>
        <Button icon="gaps" onClick={() => navigate('/information-gaps')}>{t.reasoning.nba.viewGaps}</Button>
      </PageHeader>

      <div className="mb-4 grid grid-cols-1 gap-4 lg:grid-cols-[1fr_1.4fr]">
        <Card solid title={t.reasoning.nba.scope} icon="filter">
          <Select value={caseId} onChange={(e) => setCaseId(e.target.value)}>
            <option value="">{t.reasoning.nba.allAuthorizedCases}</option>
            {cases.map((c) => <option key={c.case_id} value={c.case_id}>{c.case_id} — {c.title}</option>)}
          </Select>
          <p className="mt-2.5 rounded-lg border border-[var(--color-success)] bg-[rgba(30,142,90,0.07)] px-3 py-2 text-[11.5px] font-semibold text-[var(--color-success)]">
            <Icon name="shield" size={12} /> {data?.constraint || t.reasoning.nba.constraintDefault}
          </p>
        </Card>
        <Card solid title={t.reasoning.nba.openGapProfile} icon="gaps" subtitle={t.reasoning.nba.openGapProfileSub}>
          {gapProfile.length === 0 && <p className="text-[13px] text-[var(--color-text-muted)]/80">{t.reasoning.nba.noOpenGaps}</p>}
          <div className="space-y-1.5">
            {gapProfile.map(([type, count]) => {
              const max = Math.max(...gapProfile.map(([, c]) => c))
              return (
                <div key={type} className="flex items-center gap-2">
                  <span className="w-52 shrink-0 truncate text-[11.5px] font-semibold text-[var(--color-text)]">{tok(t.tokens.insufficientReason, type)}</span>
                  <div className="h-2 flex-1 overflow-hidden rounded-full bg-[var(--color-primary-soft)]">
                    <div className="h-full rounded-full bg-[var(--color-warning)]" style={{ width: `${(count / max) * 100}%` }} />
                  </div>
                  <span className="w-6 text-right text-[11.5px] font-bold text-[var(--color-primary-deep)]">{count}</span>
                </div>
              )
            })}
          </div>
        </Card>
      </div>

      {loading && <LoadingBlock label={t.reasoning.nba.ranking} rows={4} />}
      {error && <ErrorState message={error} onRetry={reload} />}
      {data && !data.sufficient && <InsufficientEvidence message={data.message}
        gap={t.reasoning.nba.insufficientGap} />}

      {data?.sufficient && data.recommended && (
        <Card solid className="mb-4" title={t.reasoning.nba.recommendedNextStep} icon="nextbest"
          subtitle={t.reasoning.nba.recommendedSub(data.recommended.action_id, data.recommended.information_value)}
          actions={<Badge tone="blue">{t.reasoning.nba.rank1}</Badge>}>
          <p className="text-[15px] font-bold text-[var(--color-primary-deep)]">{data.recommended.title}</p>
          <p className="mt-1 text-[13px] text-[var(--color-text)]">{data.explanation}</p>
          <p className="mt-1.5 text-[12.5px] text-[var(--color-text-muted)]/85">{data.recommended.rationale}</p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {(data.recommended.addresses || []).map((a: string) => (
              <span key={a} className="rounded-md bg-[rgba(184,121,26,0.06)] px-2 py-1 text-[11px] font-semibold text-[var(--color-warning)] ring-1 ring-[var(--color-warning)]">{t.reasoning.nba.closes}: {tok(t.tokens.insufficientReason, a)}</span>
            ))}
          </div>
          {can('analysis:run') && (
            <Button className="mt-3" variant="primary" icon="play" loading={running === data.recommended.action_id}
              onClick={() => runAction(data.recommended)}>{t.reasoning.nba.executeRecommended}</Button>
          )}
        </Card>
      )}

      <div className="space-y-3">
        {data && (data.actions?.length ?? 0) === 0 && (
          <EmptyState
            title={t.common.noData}
            message={t.reasoning.nba.noOpenGaps}
            icon="nextbest"
          />
        )}
        {(data?.actions || []).map((a: any) => (
          <Card solid key={a.action_id} title={`${a.rank}. ${a.title}`} icon="target"
            subtitle={t.reasoning.nba.closesGaps(a.action_id, a.open_gaps_addressed)}
            actions={
              <div className="flex items-center gap-1.5">
                <Badge tone="blue">IV {a.information_value}</Badge>
                {executed[a.action_id] && <Badge tone="green">{t.reasoning.nba.executed}</Badge>}
              </div>
            }>
            <div className="flex items-center gap-2">
              <div className="h-2 flex-1 overflow-hidden rounded-full bg-[var(--color-primary-soft)]">
                <div className="h-full rounded-full bg-[var(--color-primary)]"
                  style={{ width: `${Math.min(100, a.information_value * 100)}%` }} />
              </div>
              <span className="w-32 text-right text-[11px] font-semibold text-[var(--color-text-muted)]/80">{t.reasoning.nba.expectedInfoValue}</span>
            </div>
            <p className="mt-2 text-[12.5px] text-[var(--color-text)]">{a.rationale}</p>
            <div className="mt-1.5 flex flex-wrap gap-1.5">
              {(a.addresses || []).map((x: string) => (
                <span key={x} className="rounded-md bg-[var(--color-surface-solid)] px-2 py-0.5 text-[10.5px] font-bold uppercase tracking-wider text-[var(--color-text-muted)] ring-1 ring-[rgba(147,194,251,0.6)]">{tok(t.tokens.insufficientReason, x)}</span>
              ))}
              {(a.case_ids || []).map((c: string) => <Badge key={c} tone="slate">{c}</Badge>)}
            </div>
            <p className="mt-1.5 font-mono text-[11px] text-[var(--color-text-muted)]/75">{a.method} {a.endpoint}</p>
            <p className="mt-1.5 rounded-lg bg-[rgba(30,142,90,0.07)] px-2.5 py-1.5 text-[11.5px] text-[var(--color-success)]">{a.authorization}</p>
            <div className="mt-2.5 flex flex-wrap gap-2">
              {can('analysis:run') && (
                <Button size="sm" variant="primary" icon="play" loading={running === a.action_id} onClick={() => runAction(a)}>{t.reasoning.nba.execute}</Button>
              )}
              <Button size="sm" icon="gaps" onClick={() => navigate('/information-gaps')}>{t.reasoning.nba.relatedGaps}</Button>
            </div>
          </Card>
        ))}
      </div>

      <Modal open={Boolean(result)} onClose={() => setResult(null)} title={t.reasoning.nba.analysisResult} subtitle={result?.title} width="max-w-3xl">
        {result && <ResultSummary payload={result.payload} />}
      </Modal>
    </>
  )
}
