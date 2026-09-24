import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useApp } from '../state/AppContext'
import { useFetch } from '../hooks/useFetch'
import { api, ApiError } from '../services/api'
import NetworkGraph from '../components/graph/NetworkGraph'
import AgentRunModal from '../components/agents/AgentRunModal'
import {
  Badge, Button, Card, EntityChip, ErrorState, InsufficientEvidence, KeyValue, LoadingBlock,
  PageHeader, ScrollTable, StatusBadge, Td, Th,
} from '../components/shared/ui'
import type { CaseOut, GraphPayload, EvidenceItem, TimelineEvent } from '../types'
import { useI18n } from '../i18n/LanguageContext'

export default function CaseDetails() {
  const { t, tok, fmt } = useI18n()
  const { caseId = '' } = useParams()
  const navigate = useNavigate()
  const { can, notify, setActiveCase } = useApp()
  const [runOpen, setRunOpen] = useState(false)
  const [busyEv, setBusyEv] = useState<string | null>(null)

  const kase = useFetch<CaseOut>(`/api/cases/${caseId}`, [caseId])
  const evidence = useFetch<EvidenceItem[]>(`/api/evidence?case_id=${caseId}`, [caseId])
  const entities = useFetch<any>(`/api/cases/${caseId}/entities`, [caseId])
  const graph = useFetch<GraphPayload>(`/api/cases/${caseId}/network`, [caseId])
  const timeline = useFetch<any>(`/api/cases/${caseId}/timeline`, [caseId])
  const gaps = useFetch<any>(`/api/cases/${caseId}/information-gaps`, [caseId])
  const nba = useFetch<any>(`/api/cases/${caseId}/next-best-action`, [caseId])

  async function process(evidenceId: string) {
    setBusyEv(evidenceId)
    try {
      const res = await api.post<any>(`/api/evidence/${evidenceId}/process`, {})
      notify('success', `${evidenceId} processed`,
        `${res.extraction?.entities?.length ?? 0} entities · ${res.graph_updates?.relationships?.length ?? 0} candidate relationships`)
      evidence.reload(); entities.reload(); graph.reload()
    } catch (err) {
      notify('error', 'Processing failed', err instanceof ApiError ? err.message : undefined)
    } finally { setBusyEv(null) }
  }

  async function integrity(evidenceId: string) {
    setBusyEv(evidenceId)
    try {
      const res = await api.post<any>(`/api/evidence/${evidenceId}/integrity-check`, {})
      notify(res.status === 'VERIFIED' ? 'success' : 'error', `${evidenceId}: ${res.status}`, res.message)
      evidence.reload()
    } catch (err) {
      notify('error', t.cases.integrityCheckFailed, err instanceof ApiError ? err.message : undefined)
    } finally { setBusyEv(null) }
  }

  if (kase.loading) return <LoadingBlock label={t.cases.loadingCase} rows={4} />
  if (kase.error) return <ErrorState message={kase.error} onRetry={kase.reload} />
  const c = kase.data
  if (!c) return null

  return (
    <>
      <PageHeader tagline={`${t.pages.caseDetails.tagline} ${c.case_id}`} title={c.title} description={c.description}>
        <Button icon="target" onClick={() => { setActiveCase(c.case_id); notify('info', t.cases.contextSetTo(c.case_id)) }}>{t.cases.setAsContext}</Button>
        <Button icon="network" onClick={() => navigate('/network')}>{t.cases.network}</Button>
        {can('analysis:run') && <Button variant="primary" icon="play" onClick={() => setRunOpen(true)}>{t.cases.analyzeCase}</Button>}
      </PageHeader>

      <div className="space-y-4">
        <Card solid title={t.cases.caseRecord} icon="cases" actions={<><StatusBadge status={c.status} /><Badge tone="amber">{c.classification}</Badge></>}>
          <KeyValue items={[
            [t.cases.kvCaseId, c.case_id],
            [t.cases.kvCaseType, t.cases.caseTypes[c.case_type] || c.case_type],
            [t.cases.kvPriority, tok(t.tokens.priority, c.priority)],
            [t.cases.kvInvestigator, c.investigator],
            [t.cases.kvCreated, fmt.date(c.created_date)],
            [t.cases.kvStatus, tok(t.tokens.caseStatus, c.status)],
            [t.cases.kvEvidenceItems, c.evidence_count],
            [t.cases.kvEntities, c.entity_count],
          ]} />
        </Card>

        <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1.5fr_1fr]">
          <Card solid title={t.cases.evidenceAwareNetwork} icon="network"
            subtitle={graph.data ? t.cases.relSubtitle(graph.data.counts.nodes, graph.data.counts.edges) : ''}
            actions={<Button size="sm" onClick={() => navigate('/network')}>{t.cases.openFullGraph}</Button>}>
            {graph.loading && <LoadingBlock rows={2} />}
            {graph.data && (graph.data.sufficient
              ? <NetworkGraph payload={graph.data} height={340} onSelectNode={() => navigate('/network')} />
              : <InsufficientEvidence message={graph.data.message} gap={t.cases.noCorroboratedRel} />)}
          </Card>

          <div className="space-y-4">
            <Card solid title={t.cases.extractedEntities} icon="entities" subtitle={entities.data ? t.cases.entitiesInCase(entities.data.count) : ''}>
              {entities.loading && <LoadingBlock rows={2} />}
              {entities.data && entities.data.count === 0 && <InsufficientEvidence message={entities.data.message} />}
              <div className="flex flex-wrap gap-1.5">
                {(entities.data?.entities || []).slice(0, 26).map((e: any) => (
                  <EntityChip key={e.id} type={e.entity_type} label={e.label} onClick={() => navigate(`/entities?focus=${e.id}`)} />
                ))}
              </div>
            </Card>

            <Card solid title={t.cases.informationGaps} icon="gaps" subtitle={gaps.data ? t.cases.openGapCount(gaps.data.gaps.length) : ''}>
              {gaps.loading && <LoadingBlock rows={1} />}
              {gaps.data?.gaps?.length === 0 && <p className="text-[13px] text-[var(--color-text-muted)]/80">{t.cases.noGapsForCase}</p>}
              <ul className="space-y-2">
                {(gaps.data?.gaps || []).slice(0, 3).map((g: any) => (
                  <li key={g.gap_id} className="rounded-lg border border-[var(--color-warning)] bg-[rgba(184,121,26,0.06)] px-3 py-2">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-[12.5px] font-bold text-[var(--color-primary-deep)]">{g.gap_id}</p>
                      <Badge tone={g.severity === 'HIGH' ? 'red' : 'amber'}>{tok(t.tokens.priority, g.severity)}</Badge>
                    </div>
                    <p className="mt-0.5 text-[12px] text-[var(--color-text)]">{g.statement}</p>
                    <p className="mt-1 text-[11.5px] text-[var(--color-text-muted)]/85">{t.cases.recommended}: {g.recommended_analysis}</p>
                  </li>
                ))}
              </ul>
            </Card>

            <Card solid title={t.cases.nextBestAction} icon="nextbest">
              {nba.loading && <LoadingBlock rows={1} />}
              {nba.data?.recommended ? (
                <div className="rounded-[12px] border border-[var(--color-primary)] bg-[var(--color-primary-soft)] px-3.5 py-3">
                  <p className="text-[13.5px] font-bold text-[var(--color-primary-deep)]">{nba.data.recommended.title}</p>
                  <p className="mt-1 text-[12px] text-[var(--color-text-muted)]/85">{nba.data.recommended.rationale}</p>
                  <Button size="sm" className="mt-2" icon="arrowRight" onClick={() => navigate('/next-best-action')}>{t.cases.openDecisionSupport}</Button>
                </div>
              ) : (
                <p className="text-[13px] text-[var(--color-text-muted)]/80">{nba.data?.message || t.cases.noActionPrioritised}</p>
              )}
            </Card>
          </div>
        </div>

        <Card solid title={t.cases.evidenceRegistry} icon="evidence"
          subtitle={t.cases.evidenceRegistrySub}
          actions={<Button size="sm" onClick={() => navigate(`/evidence?case=${c.case_id}`)}>{t.cases.evidenceWorkspace}</Button>}>
          {evidence.loading && <LoadingBlock rows={2} />}
          {evidence.data && evidence.data.length === 0 && (
            <InsufficientEvidence message={t.cases.noEvidenceForCase} gap={t.cases.registerFirstEvidence} />
          )}
          {evidence.data && evidence.data.length > 0 && (
            <ScrollTable>
              <thead>
                <tr><Th>{t.cases.thEvidence}</Th><Th>{t.cases.thType}</Th><Th>{t.cases.thSource}</Th><Th>{t.cases.thProcessing}</Th><Th>{t.cases.thIntegrity}</Th><Th>{t.cases.thVerification}</Th><Th>{t.cases.thActions}</Th></tr>
              </thead>
              <tbody>
                {evidence.data.map((e) => (
                  <tr key={e.evidence_id} className="transition hover:bg-[var(--color-primary-soft)]/50">
                    <Td><span className="font-semibold">{e.evidence_id}</span><br /><span className="text-[11px] text-[var(--color-text-muted)]/70">{fmt.dateTime(e.timestamp)}</span></Td>
                    <Td>{tok(t.tokens.evidenceType, e.evidence_type)}</Td>
                    <Td className="max-w-[180px] truncate">{e.source}</Td>
                    <Td><StatusBadge status={e.processing_status} /></Td>
                    <Td><StatusBadge status={e.integrity_status} /></Td>
                    <Td><StatusBadge status={e.verification_status} /></Td>
                    <Td>
                      <div className="flex flex-wrap gap-1.5">
                        {can('evidence:process') && (
                          <Button size="sm" icon="spark" loading={busyEv === e.evidence_id} onClick={() => process(e.evidence_id)}>{t.cases.process}</Button>
                        )}
                        {can('evidence:integrity') && (
                          <Button size="sm" icon="hash" loading={busyEv === e.evidence_id} onClick={() => integrity(e.evidence_id)}>{t.cases.integrity}</Button>
                        )}
                      </div>
                    </Td>
                  </tr>
                ))}
              </tbody>
            </ScrollTable>
          )}
        </Card>

        <Card solid title={t.cases.caseTimeline} icon="timeline" subtitle={timeline.data ? t.cases.eventCount(timeline.data.count) : ''}
          actions={<Button size="sm" onClick={() => navigate('/timeline')}>{t.cases.temporalAnalysis}</Button>}>
          {timeline.loading && <LoadingBlock rows={2} />}
          {timeline.data && !timeline.data.sufficient && <InsufficientEvidence message={timeline.data.message} />}
          {timeline.data?.events?.length > 0 && (
            <ol className="space-y-2 border-l-2 border-[var(--color-border)] pl-4">
              {timeline.data.events.map((e: TimelineEvent) => (
                <li key={e.event_id} className="relative">
                  <span className="absolute -left-[21px] top-1.5 h-2.5 w-2.5 rounded-full border-2 border-white bg-[var(--color-primary-soft)]0" />
                  <p className="text-[13px] font-semibold text-[var(--color-primary-deep)]">{e.title}</p>
                  <p className="text-[11.5px] text-[var(--color-text-muted)]/80">
                    {e.timestamp.replace('T', ' ').replace('Z', '')} · {e.event_type} · {e.evidence_id || 'no evidence ref'}
                  </p>
                </li>
              ))}
            </ol>
          )}
        </Card>
      </div>

      <AgentRunModal open={runOpen} onClose={() => { setRunOpen(false); graph.reload(); gaps.reload(); nba.reload() }}
        objective="FULL_CASE_ANALYSIS" caseIds={[c.case_id]} />
    </>
  )
}
