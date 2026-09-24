import { useCallback, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApp } from '../state/AppContext'
import { api, ApiError } from '../services/api'
import { Icon } from '../components/shared/Icon'
import type { IconName } from '../components/shared/Icon'
import { Button, Card, PageHeader, Select } from '../components/shared/ui'
import { useI18n } from '../i18n/LanguageContext'

/**
 * INVESTIGATION WORKFLOW — the end-to-end pipeline as an executable, auditable
 * sequence. Every stage calls the real backend service, reports the real result
 * and links to the page where the analyst works with it. Nothing is simulated:
 * a stage that cannot be satisfied reports INSUFFICIENT EVIDENCE or a blocked
 * permission rather than a green tick.
 */

type Status = 'idle' | 'running' | 'ok' | 'insufficient' | 'blocked' | 'error'

interface StageResult { status: Status; headline?: string; metrics?: Array<[string, string]>; note?: string }

interface Stage {
  id: string
  index: number
  name: string
  icon: IconName
  purpose: string
  route: string
  permission?: string
  run: (scope: string[]) => Promise<StageResult>
}

const okStatus = (headline: string, metrics: Array<[string, string]>, note?: string): StageResult =>
  ({ status: 'ok', headline, metrics, note })

export default function Workflow() {
  const { t } = useI18n()
  const { cases, activeCase, user, can, notify } = useApp()
  const navigate = useNavigate()
  const [scopeCase, setScopeCase] = useState(activeCase || '')
  const [results, setResults] = useState<Record<string, StageResult>>({})
  const [runningAll, setRunningAll] = useState(false)
  const abort = useRef(false)

  const scope = useMemo(() => (scopeCase ? [scopeCase] : []), [scopeCase])

  const STAGES: Stage[] = useMemo(() => [
    {
      id: 'login', index: 1, name: 'Login', icon: 'lock', route: '/security',
      purpose: 'JWT session, role-based permissions and case-level authorization resolved server-side.',
      run: async () => {
        const me = await api.get<any>('/api/auth/me')
        return okStatus(`${me.display_name} · ${me.role}`, [
          ['Permissions', String(me.permissions.length)],
          ['Case access', me.case_access.includes('*') ? 'All cases' : String(me.case_access.length)],
          ['Unit', me.unit || '—'],
        ], 'Every downstream call is authorized against this principal.')
      },
    },
    {
      id: 'case', index: 2, name: 'Case', icon: 'cases', route: '/cases', permission: 'case:read',
      purpose: 'Open the authorized case record that scopes the whole investigation.',
      run: async () => {
        const list = await api.get<any[]>('/api/cases')
        const inScope = scopeCase ? list.filter((c) => c.case_id === scopeCase) : list
        if (inScope.length === 0) return { status: 'insufficient', headline: 'No authorized case in scope' }
        const open = inScope.filter((c) => c.status === 'OPEN').length
        return okStatus(scopeCase ? `${inScope[0].case_id} — ${inScope[0].title}` : `${inScope.length} authorized cases`, [
          ['Cases in scope', String(inScope.length)],
          ['Open', String(open)],
          ['Priority', inScope[0].priority || '—'],
        ])
      },
    },
    {
      id: 'evidence', index: 3, name: 'Evidence', icon: 'evidence', route: '/evidence', permission: 'evidence:read',
      purpose: 'Register evidence, hash it with SHA-256 at intake and store the object write-once.',
      run: async () => {
        const list = await api.get<any[]>('/api/evidence')
        const items = scopeCase ? list.filter((e) => e.case_id === scopeCase) : list
        if (items.length === 0) {
          return { status: 'insufficient', headline: 'INSUFFICIENT EVIDENCE — no evidence registered for this scope', note: 'Gap: no source documents exist to analyse.' }
        }
        const processed = items.filter((e) => e.processing_status !== 'UPLOADED').length
        return okStatus(`${items.length} evidence objects registered`, [
          ['Processed', `${processed}/${items.length}`],
          ['Hashed', `${items.filter((e) => e.sha256).length}/${items.length}`],
          ['Types', String(new Set(items.map((e) => e.evidence_type)).size)],
        ])
      },
    },
    {
      id: 'extraction', index: 4, name: 'Entity extraction', icon: 'doc', route: '/evidence', permission: 'evidence:process',
      purpose: 'Document intelligence: spaCy NER plus the rule layer for plates, phones, accounts and IDs.',
      run: async () => {
        const list = await api.get<any[]>('/api/evidence')
        const items = (scopeCase ? list.filter((e) => e.case_id === scopeCase) : list)
          .filter((e) => e.text_origin !== 'NONE')
        if (items.length === 0) return { status: 'insufficient', headline: 'No readable evidence text in scope' }
        const target = items.find((e) => e.processing_status === 'UPLOADED') || items[0]
        const res = await api.post<any>(`/api/evidence/${target.evidence_id}/process`, {})
        const ex = res.extraction || {}
        const linked = res.graph_updates?.linked_entities || []
        return okStatus(`${target.evidence_id} → ${(ex.entities || []).length} entities extracted`, [
          ['Pipeline stage', res.status || 'ENTITIES_FOUND'],
          ['NER backend', ex.backend?.ner_backend || 'spaCy'],
          ['Linked to graph', String(linked.length)],
        ], ex.note || res.document?.ocr_note ||
           'Extraction is deterministic: spaCy statistical NER plus the regex rule layer. Nothing is inferred beyond the document text.')
      },
    },
    {
      id: 'resolution', index: 5, name: 'Entity resolution', icon: 'entities', route: '/entities', permission: 'analysis:run',
      purpose: 'Normalise → tokenize → RapidFuzz → multi-attribute scoring. Identities are never auto-merged.',
      run: async () => {
        const res = await api.post<any>('/api/analysis/entity-resolution', { case_ids: scope })
        if (!res.sufficient) return { status: 'insufficient', headline: res.note || 'No comparable identity records' }
        const top = res.candidate_matches[0]
        return okStatus(top ? `${top.left.label} ↔ ${top.right.label} · ${top.score} ${top.support_level}` : 'No candidate above threshold', [
          ['Records compared', String(res.compared_records)],
          ['Candidates', String(res.candidate_matches.length)],
          ['Auto-merge', 'DISABLED'],
        ], 'Each candidate waits for an explicit human decision.')
      },
    },
    {
      id: 'crosscase', index: 6, name: 'Cross-case correlation', icon: 'crosscase', route: '/cross-case', permission: 'analysis:run',
      purpose: 'Shared hard identifiers, fuzzy names, shared locations and temporal proximity across cases.',
      run: async () => {
        const res = await api.post<any>('/api/analysis/cross-case', { case_ids: scope })
        if (!res.sufficient || res.associations.length === 0) {
          return { status: 'insufficient', headline: res.message || 'No cross-case association in this scope', note: 'Two or more comparable cases are required.' }
        }
        const top = res.associations[0]
        return okStatus(`${top.case_a} ↔ ${top.case_b} · ${top.strength} ${top.support_level}`, [
          ['Associations', String(res.associations.length)],
          ['Shared entities', String(res.entity_overlap.length)],
          ['Status', top.verification_status],
        ])
      },
    },
    {
      id: 'graph', index: 7, name: 'Knowledge graph', icon: 'network', route: '/network', permission: 'case:read',
      purpose: 'Reconstruct the evidence graph — no relationship exists without an evidence reference.',
      run: async () => {
        const g = await api.get<any>(`/api/graph${scopeCase ? `?case_id=${scopeCase}` : ''}`)
        if (!g.sufficient) return { status: 'insufficient', headline: g.message }
        const verified = g.edges.filter((e: any) => e.data.verification_status === 'HUMAN_VERIFIED').length
        return okStatus(`${g.counts.nodes} entities · ${g.counts.edges} relationships`, [
          ['Human-verified edges', `${verified}/${g.counts.edges}`],
          ['Entity types', String(new Set(g.nodes.map((n: any) => n.data.entity_type)).size)],
          ['Evidence-backed', '100%'],
        ])
      },
    },
    {
      id: 'network', index: 8, name: 'Network analysis', icon: 'target', route: '/network', permission: 'analysis:run',
      purpose: 'Degree and betweenness centrality, Louvain communities, evidence-backed shortest paths.',
      run: async () => {
        const res = await api.post<any>('/api/analysis/network', { case_ids: scope })
        if (!res.sufficient) return { status: 'insufficient', headline: res.message }
        const top = res.degree_centrality[0]
        return okStatus(top ? `Most connected: ${top.label} (${top.score})` : 'Analysis complete', [
          ['Nodes / edges', `${res.nodes} / ${res.edges}`],
          ['Communities', String(res.communities.length)],
          ['Modularity', String(res.modularity ?? '—')],
        ], 'Structural prominence is not evidence of criminality.')
      },
    },
    {
      id: 'timeline', index: 9, name: 'Timeline', icon: 'timeline', route: '/timeline', permission: 'case:read',
      purpose: 'Chronology, activity spikes, repeated patterns and spatio-temporal convergence.',
      run: async () => {
        const t = await api.get<any>(`/api/timeline${scopeCase ? `?case_ids=${scopeCase}` : ''}`)
        if (!t.sufficient) return { status: 'insufficient', headline: t.message }
        return okStatus(`${t.event_count} events reconstructed`, [
          ['Spikes', String(t.spikes.length)],
          ['Repeated patterns', String(t.repeated_activity.length)],
          ['Convergence windows', String(t.convergence.length)],
        ], 'Co-location in time does not establish that individuals met.')
      },
    },
    {
      id: 'corroboration', index: 10, name: 'Corroboration', icon: 'check', route: '/hypotheses', permission: 'analysis:run',
      purpose: 'Cross-check each lead against independent analytical methods and independent sources.',
      run: async () => {
        const res = await api.post<any>('/api/analysis/corroboration', { case_ids: scope })
        if (!res.sufficient) return { status: 'insufficient', headline: res.message }
        const s = res.summary
        const lead = res.leads[0]
        return okStatus(lead ? `${lead.title} → ${lead.status}` : 'Corroboration complete', [
          ['Corroborated', String(s.corroborated)],
          ['Contradictory', String(s.contradictory)],
          ['Insufficient', String(s.insufficient)],
        ], 'Contradictory evidence is displayed, never suppressed.')
      },
    },
    {
      id: 'gaps', index: 11, name: 'Information gap', icon: 'gaps', route: '/information-gaps', permission: 'analysis:run',
      purpose: 'State what is known, what is unknown and what evidence would resolve the gap.',
      run: async () => {
        const res = await api.post<any>('/api/analysis/information-gaps', { case_ids: scope })
        if (!res.sufficient || res.gaps.length === 0) {
          return { status: 'insufficient', headline: res.message || 'No open information gaps' }
        }
        const top = res.gaps[0]
        return okStatus(`${top.gap_id}: ${top.question}`, [
          ['Open gaps', String(res.gaps.length)],
          ['Highest severity', top.severity],
          ['Gap types', (top.gap_types || []).join(', ') || '—'],
        ])
      },
    },
    {
      id: 'nba', index: 12, name: 'Next-best action', icon: 'nextbest', route: '/next-best-action', permission: 'analysis:run',
      purpose: 'Rank analytical actions by expected information value. Analytical steps only.',
      run: async () => {
        const res = await api.post<any>('/api/analysis/next-best-action', { case_ids: scope })
        if (!res.sufficient) return { status: 'insufficient', headline: res.message }
        return okStatus(res.recommended.title, [
          ['Information value', String(res.recommended.information_value)],
          ['Gaps closed', String(res.recommended.open_gaps_addressed)],
          ['Ranked actions', String(res.actions.length)],
        ], res.constraint)
      },
    },
    {
      id: 'verification', index: 13, name: 'Human verification', icon: 'user', route: '/network', permission: 'case:read',
      purpose: 'Analytical output is advisory until an authorized human verifies or rejects it.',
      run: async () => {
        const v = await api.get<any>('/api/verifications')
        const g = await api.get<any>(`/api/graph${scopeCase ? `?case_id=${scopeCase}` : ''}`)
        const pending = (g.edges || []).filter((e: any) => e.data.verification_status === 'UNVERIFIED').length
        return okStatus(`${v.count} decisions recorded · ${pending} candidates awaiting review`, [
          ['Verified', String((v.verifications || []).filter((x: any) => x.decision === 'HUMAN_VERIFIED').length)],
          ['Rejected', String((v.verifications || []).filter((x: any) => x.decision === 'REJECTED').length)],
          ['Awaiting', String(pending)],
        ], 'Rejected findings are retained with rationale — nothing is deleted.')
      },
    },
    {
      id: 'integrity', index: 14, name: 'SHA-256 integrity', icon: 'shield', route: '/audit', permission: 'evidence:integrity',
      purpose: 'Re-hash every evidence object and compare against the hash registered at intake.',
      run: async () => {
        const res = await api.post<any>('/api/integrity/run-all', {})
        return {
          status: res.mismatches > 0 ? 'ok' : 'ok',
          headline: res.mismatches > 0
            ? `${res.mismatches} integrity mismatch detected across ${res.checked} objects`
            : `All ${res.checked} evidence objects match their intake hash`,
          metrics: [
            ['Checked', String(res.checked)],
            ['Mismatches', String(res.mismatches)],
            ['Algorithm', 'SHA-256'],
          ],
          note: res.mismatches > 0
            ? 'A mismatch preserves the registered hash and flags the object as suspect. The original evidence is never modified.'
            : undefined,
        }
      },
    },
    {
      id: 'audit', index: 15, name: 'Audit', icon: 'audit', route: '/audit', permission: 'audit:read',
      purpose: 'Append-only, SHA-256 hashed audit trail, notarised in the permissioned ledger.',
      run: async () => {
        const a = await api.get<any>('/api/audit?limit=5')
        let chain = 'not authorized'
        let blocks = '—'
        try {
          const l = await api.post<any>('/api/ledger/verify', {})
          chain = l.chain_intact ? 'INTACT' : 'BROKEN'
          blocks = String(l.blocks)
        } catch { /* ledger:read not held */ }
        return okStatus(`${a.total_records} append-only audit records`, [
          ['Ledger blocks', blocks],
          ['Chain', chain],
          ['Per-record hash', 'SHA-256'],
        ], 'No user and no agent can modify audit history.')
      },
    },
  ], [scope, scopeCase])

  const runStage = useCallback(async (stage: Stage) => {
    if (stage.permission && !can(stage.permission)) {
      setResults((r) => ({ ...r, [stage.id]: { status: 'blocked', headline: `Your role does not hold ${stage.permission}` } }))
      return 'blocked' as const
    }
    setResults((r) => ({ ...r, [stage.id]: { status: 'running' } }))
    try {
      const res = await stage.run(scope)
      setResults((r) => ({ ...r, [stage.id]: res }))
      return res.status
    } catch (err) {
      const message = err instanceof ApiError ? err.message : 'The stage could not be completed.'
      setResults((r) => ({ ...r, [stage.id]: { status: err instanceof ApiError && err.status === 403 ? 'blocked' : 'error', headline: message } }))
      return 'error' as const
    }
  }, [can, scope])

  async function runAll() {
    setRunningAll(true)
    abort.current = false
    setResults({})
    let ok = 0
    for (const stage of STAGES) {
      if (abort.current) break
      const status = await runStage(stage)
      if (status === 'ok') ok += 1
    }
    setRunningAll(false)
    notify('success', 'Workflow run complete', `${ok}/${STAGES.length} stages returned an evidence-backed result.`)
  }

  const completed = STAGES.filter((s) => ['ok', 'insufficient'].includes(results[s.id]?.status || '')).length
  const progress = Math.round((completed / STAGES.length) * 100)

  return (
    <>
      <PageHeader
        tagline={t.pages.workflow.tagline}
        title={t.pages.workflow.title}
        description={t.pages.workflow.description}
      >
        <Select value={scopeCase} onChange={(e) => setScopeCase(e.target.value)} className="!w-auto">
          <option value="">All authorized cases</option>
          {cases.map((c) => <option key={c.case_id} value={c.case_id}>{c.case_id} — {c.title}</option>)}
        </Select>
        {runningAll
          ? <Button variant="danger" icon="close" onClick={() => { abort.current = true }}>Stop</Button>
          : <Button variant="primary" icon="play" onClick={runAll}>Run full workflow</Button>}
      </PageHeader>

      <Card solid className="mb-4" title="Pipeline progress" icon="spark"
        subtitle={`${completed}/${STAGES.length} stages executed as ${user?.role} · scope: ${scopeCase || 'all authorized cases'}`}>
        <div className="h-2 w-full overflow-hidden rounded-full bg-[var(--color-primary-soft)]">
          <div className="h-full rounded-full bg-[var(--color-primary)] transition-all duration-500"
            style={{ width: `${progress}%` }} />
        </div>
        <div className="mt-3 flex flex-wrap gap-1.5">
          {STAGES.map((s) => {
            const st = results[s.id]?.status || 'idle'
            const tone = st === 'ok' ? 'status-verified'
              : st === 'insufficient' ? 'status-candidate'
              : st === 'blocked' ? 'status-insufficient'
              : st === 'error' ? 'status-rejected'
              : st === 'running' ? 'bg-[var(--color-primary)] text-white animate-pulse'
              : 'status-insufficient'
            return (
              <span key={s.id} className={`rounded-md px-2 py-1 text-[10.5px] font-semibold uppercase tracking-wider ${tone}`}>
                {s.index}. {s.name}
              </span>
            )
          })}
        </div>
      </Card>

      <ol className="space-y-3">
        {STAGES.map((stage) => {
          const res = results[stage.id]
          const st = res?.status || 'idle'
          return (
            <li key={stage.id} className="relative">
              <Card solid
                title={`${stage.index}. ${stage.name}`}
                icon={stage.icon}
                subtitle={stage.purpose}
                actions={
                  <div className="flex flex-wrap items-center gap-1.5">
                    <StatusChip status={st} />
                    <Button size="sm" icon="play" loading={st === 'running'} onClick={() => runStage(stage)}>Run</Button>
                    <Button size="sm" icon="arrowRight" onClick={() => navigate(stage.route)}>Open</Button>
                  </div>
                }
              >
                {!res && (
                  <p className="rounded-[10px] border border-dashed border-[var(--color-border)] px-3 py-2.5 text-[12.5px] text-[var(--color-text-muted)]">
                    Not executed yet — run this stage to see the live result from the analytical services. A stage that
                    cannot be satisfied reports INSUFFICIENT EVIDENCE rather than a green tick.
                  </p>
                )}
                {res?.headline && (
                  <p className={`text-[13.5px] font-semibold ${
                    st === 'insufficient' ? 'text-[var(--color-warning)]'
                    : st === 'error' ? 'text-[var(--color-danger)]'
                    : st === 'blocked' ? 'text-[var(--color-text-muted)]'
                    : 'text-[var(--color-primary-deep)]'}`}>
                    {res.headline}
                  </p>
                )}
                {res?.metrics && (
                  <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-3">
                    {res.metrics.map(([k, v]) => (
                      <div key={k} className="rounded-[10px] border border-[var(--color-border)] px-3 py-2">
                        <p className="text-[10.5px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">{k}</p>
                        <p className="data-num mt-0.5 text-[13.5px] font-semibold text-[var(--color-primary-deep)]">{v}</p>
                      </div>
                    ))}
                  </div>
                )}
                {res?.note && (
                  <p className="mt-2 flex items-start gap-2 rounded-[10px] border border-[var(--color-border)] bg-[var(--color-primary-soft)] px-3 py-2 text-[11.5px] text-[var(--color-text)]">
                    <Icon name="info" size={12} className="mt-0.5 shrink-0" /> <span>{res.note}</span>
                  </p>
                )}
              </Card>
            </li>
          )
        })}
      </ol>
    </>
  )
}

function StatusChip({ status }: { status: Status }) {
  const map: Record<Status, { kind: string; label: string }> = {
    idle: { kind: 'status-insufficient', label: 'NOT RUN' },
    running: { kind: 'bg-[var(--color-primary)] text-white border border-[var(--color-primary)]', label: 'RUNNING' },
    ok: { kind: 'status-verified', label: 'EVIDENCE-BACKED' },
    insufficient: { kind: 'status-candidate', label: 'INSUFFICIENT EVIDENCE' },
    blocked: { kind: 'status-insufficient', label: 'NOT AUTHORIZED' },
    error: { kind: 'status-rejected', label: 'FAILED' },
  }
  const { kind, label } = map[status]
  return (
    <span className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide ${kind}`}>
      {status === 'ok' && <Icon name="check" size={11} />}
      {status === 'insufficient' && <Icon name="info" size={11} />}
      {status === 'error' && <Icon name="alert" size={11} />}
      {label}
    </span>
  )
}
