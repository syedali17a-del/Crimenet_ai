import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, ApiError } from '../../services/api'
import type { ManagerRun } from '../../types'
import { Icon } from '../shared/Icon'
import { Badge, Button, ErrorState, Modal, Spinner } from '../shared/ui'
import { useApp } from '../../state/AppContext'
import { useI18n } from '../../i18n/LanguageContext'

type Objective = 'CROSS_CASE_LINK' | 'FULL_CASE_ANALYSIS' | 'EVIDENCE_INTEGRITY_SWEEP'

interface PlanTask { task_id: string; name: string; service: string; agent: string; label: string; depends_on: string[] }

export default function AgentRunModal({
  open, onClose, objective, caseIds, onComplete,
}: {
  open: boolean
  onClose: () => void
  objective: Objective
  caseIds: string[]
  onComplete?: (run: ManagerRun) => void
}) {
  const { t, tok } = useI18n()
  const { notify } = useApp()
  const navigate = useNavigate()
  const [plan, setPlan] = useState<PlanTask[]>([])
  const [progress, setProgress] = useState(0)
  const [run, setRun] = useState<ManagerRun | null>(null)
  const [error, setError] = useState<string | null>(null)
  const timer = useRef<number | null>(null)

  useEffect(() => {
    if (!open) return
    let cancelled = false
    setRun(null); setError(null); setProgress(0); setPlan([])

    async function go() {
      try {
        const p = await api.post<{ tasks: PlanTask[] }>('/api/analysis/manager/plan', { objective, case_ids: caseIds })
        if (cancelled) return
        setPlan(p.tasks)
        timer.current = window.setInterval(() => {
          setProgress((v) => (v < p.tasks.length - 1 ? v + 1 : v))
        }, 430)
        const result = await api.post<ManagerRun>('/api/analysis/manager/execute', { objective, case_ids: caseIds })
        if (cancelled) return
        if (timer.current) window.clearInterval(timer.current)
        setProgress(p.tasks.length)
        setRun(result)
        onComplete?.(result)
        notify('success', t.reasoning.agent.analysisComplete, result.conclusion.headline)
      } catch (err) {
        if (cancelled) return
        if (timer.current) window.clearInterval(timer.current)
        setError(err instanceof ApiError ? err.message : t.reasoning.agent.failed)
      }
    }
    go()
    return () => {
      cancelled = true
      if (timer.current) window.clearInterval(timer.current)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, objective, caseIds.join(',')])

  const tasks = useMemo(() => {
    if (run) return run.tasks.map((t) => ({
      id: t.task_id, name: t.name, agent: t.agent, status: t.status, summary: t.summary,
      label: '',
    }))
    return plan.map((t, i) => ({
      id: t.task_id, name: t.name, agent: t.agent, label: t.label, summary: '',
      status: i < progress ? 'COMPLETE' : i === progress ? 'RUNNING' : 'PENDING',
    }))
  }, [run, plan, progress])

  const title = run ? t.reasoning.agent.titleComplete : t.reasoning.agent.titleRunning

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={title}
      subtitle={t.reasoning.agent.subtitle(objective.replace(/_/g, ' ').toLowerCase(), caseIds.join(', ') || t.reasoning.agent.allAuthorizedCases)}
      width="max-w-3xl"
      footer={
        <>
          {run && (
            <>
              <Button size="sm" icon="gaps" onClick={() => { onClose(); navigate('/information-gaps') }}>{t.reasoning.agent.informationGaps}</Button>
              <Button size="sm" icon="nextbest" onClick={() => { onClose(); navigate('/next-best-action') }}>{t.reasoning.agent.nextBestAction}</Button>
              <Button size="sm" icon="network" onClick={() => { onClose(); navigate('/network') }}>{t.reasoning.agent.openNetwork}</Button>
            </>
          )}
          <Button size="sm" variant={run ? 'primary' : 'neu'} onClick={onClose}>{run ? t.reasoning.agent.close : t.reasoning.agent.runInBackground}</Button>
        </>
      }
    >
      {error ? (
        <ErrorState message={error} />
      ) : (
        <div className="space-y-4">
          {!run && (
            <div className="flex items-center gap-2.5 rounded-lg border border-[var(--color-border)] bg-[var(--color-primary-soft)]/70 px-3 py-2.5">
              <Spinner size={16} />
              <p className="text-[13px] font-medium text-[var(--color-primary-deep)]">
                Manager Agent — planning investigation, delegating to authorized analytical services…
              </p>
            </div>
          )}

          <ol className="space-y-1.5">
            {tasks.map((task) => {
              const done = task.status === 'COMPLETE'
              const running = task.status === 'RUNNING'
              const skipped = task.status === 'SKIPPED'
              const failed = task.status === 'FAILED'
              return (
                <li
                  key={task.id}
                  className={`flex items-start gap-3 rounded-lg border px-3 py-2.5 transition-all duration-300 ${
                    running ? 'border-[var(--color-primary)] bg-[var(--color-primary-soft)]/80'
                      : done ? 'border-[var(--color-success)] bg-[rgba(30,142,90,0.07)]'
                      : failed ? 'border-[var(--color-danger)] bg-[rgba(196,52,31,0.06)]'
                      : skipped ? 'border-[var(--color-warning)] bg-[rgba(184,121,26,0.06)]'
                      : 'border-[rgba(147,194,251,0.4)] bg-white/60 opacity-70'
                  }`}
                >
                  <span className={`mt-0.5 shrink-0 ${done ? 'text-[var(--color-success)]' : running ? 'text-[var(--color-primary)]' : failed ? 'text-rose-600' : skipped ? 'text-amber-600' : 'text-[rgba(91,107,133,0.35)]'}`}>
                    {running ? <Spinner size={15} /> : <Icon name={done ? 'check' : failed ? 'alert' : skipped ? 'lock' : 'clock'} size={15} />}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                      <p className="text-[13px] font-semibold text-[var(--color-primary-deep)]">{task.name}</p>
                      <Badge tone="blue">{tok(t.tokens.agent, task.agent)}</Badge>
                      {skipped && <Badge tone="amber">{t.reasoning.agent.withheld}</Badge>}
                      {failed && <Badge tone="red">{t.reasoning.agent.stepFailed}</Badge>}
                    </div>
                    <p className="mt-0.5 break-words text-[12px] leading-snug text-[var(--color-text-muted)]/85">
                      {task.summary || task.label || (running ? t.reasoning.agent.running : t.reasoning.agent.queued)}
                    </p>
                  </div>
                </li>
              )
            })}
            {tasks.length === 0 && <LoadingSkeleton />}
          </ol>

          {run && (
            <div className="glass rounded-xl px-4 py-3.5">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="card-title">{t.reasoning.agent.structuredResult}</p>
                <Badge tone={run.conclusion.status.includes('CORROBORATED') ? 'green' : run.conclusion.status.includes('CONTRADICT') ? 'red' : 'amber'}>
                  {tok(t.tokens.leadStatus, run.conclusion.status)}
                </Badge>
              </div>
              <p className="mt-1.5 text-[14px] font-bold text-[var(--color-primary-deep)]">{run.conclusion.headline}</p>
              <p className="mt-1 text-[12.5px] text-[var(--color-text-muted)]/85">{run.conclusion.corroboration_summary}</p>
              {run.conclusion.why && run.conclusion.why.length > 0 && (
                <ul className="mt-2 space-y-0.5">
                  {run.conclusion.why.slice(0, 5).map((w) => (
                    <li key={w} className="flex items-start gap-1.5 text-[12.5px] text-[var(--color-text)]">
                      <span className="mt-0.5 text-[var(--color-success)]"><Icon name="check" size={13} /></span>{w}
                    </li>
                  ))}
                </ul>
              )}
              {run.conclusion.missing_evidence && run.conclusion.missing_evidence.length > 0 && (
                <div className="mt-2 rounded-lg border border-[var(--color-warning)] bg-[rgba(184,121,26,0.06)] px-3 py-2">
                  <p className="text-[11px] font-bold uppercase tracking-wider text-[var(--color-warning)]">{t.reasoning.agent.missingInformation}</p>
                  <ul className="mt-1 space-y-0.5">
                    {run.conclusion.missing_evidence.map((m) => (
                      <li key={m} className="text-[12.5px] text-[var(--color-text)]">? {m}</li>
                    ))}
                  </ul>
                </div>
              )}
              <div className="mt-2.5 flex flex-wrap items-center gap-2 text-[12px] text-[var(--color-text-muted)]/85">
                <Badge tone="slate">{t.reasoning.agent.openGapCount(run.conclusion.open_gaps)}</Badge>
                {run.conclusion.recommended_next_analysis && (
                  <span><span className="font-semibold text-[var(--color-primary-deep)]">{t.reasoning.agent.recommendedNext}:</span> {run.conclusion.recommended_next_analysis}</span>
                )}
              </div>
              <p className="mt-2.5 border-t border-[rgba(147,194,251,0.4)] pt-2 text-[11.5px] italic text-[var(--color-text-muted)]/75">
                {run.conclusion.principle}
              </p>
            </div>
          )}
        </div>
      )}
    </Modal>
  )
}

function LoadingSkeleton() {
  return (
    <>
      {Array.from({ length: 5 }).map((_, i) => (
        <li key={i} className="skeleton h-12 rounded-lg" />
      ))}
    </>
  )
}
