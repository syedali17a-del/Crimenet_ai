import { useEffect, useState } from 'react'
import { api, ApiError } from '../../services/api'
import { useApp } from '../../state/AppContext'
import { Icon } from '../shared/Icon'
import {
  Badge, Button, EntityChip, ErrorState, Hash, KeyValue, LoadingBlock, MaskedValue,
  SourceTrustBadge, StatusPill, SupportBadge, TextArea,
} from '../shared/ui'

/* ============================================================================
   INSPECTOR DRAWER
   Glass shell (allowed), but every block of small text inside it sits on an
   opaque surface. The A2 structural explanation — why the backend ranks this
   node where it ranks it — is the first thing in the drawer, above the raw
   relationship list, because that is the question an investigator opens a node
   to answer.
   ============================================================================ */

interface Props {
  entityId: string | null
  onClose: () => void
  onSelectEntity?: (id: string) => void
  onChanged?: () => void
  /** A2: per-node explanation returned by /api/analysis/network */
  structuralExplanation?: { degree?: string; betweenness?: string; score?: string } | null
  analysisReady?: boolean
  onRunAnalysis?: () => void
  analysing?: boolean
}

export default function EntityPanel({
  entityId, onClose, onSelectEntity, onChanged,
  structuralExplanation, analysisReady = false, onRunAnalysis, analysing = false,
}: Props) {
  const { can, notify } = useApp()
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState<string | null>(null)
  // A6 — masked identifiers: the full value is fetched only through the audited
  // reveal action, and the button says so before it is pressed.
  const [revealed, setRevealed] = useState<{ value: string; masked_form?: string } | null>(null)
  const [revealBusy, setRevealBusy] = useState(false)

  async function load() {
    if (!entityId) return
    setLoading(true); setError(null)
    try {
      setData(await api.get<any>(`/api/entities/${entityId}`))
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Entity could not be loaded.')
    } finally { setLoading(false) }
  }

  useEffect(() => { setData(null); setNote(''); setRevealed(null); load() /* eslint-disable-next-line */ }, [entityId])

  async function revealIdentifier() {
    if (!entityId) return
    setRevealBusy(true)
    try {
      const res = await api.get<any>(`/api/entities/${entityId}/reveal`)
      setRevealed(res)
      notify('success', 'Identifier revealed', 'This reveal is recorded in the audit trail and the ledger.')
    } catch (err) {
      notify('error', 'Reveal not permitted', err instanceof ApiError ? err.message : undefined)
    } finally { setRevealBusy(false) }
  }

  async function decide(kind: 'verify' | 'reject') {
    if (!entityId) return
    setBusy(kind)
    try {
      await api.post(`/api/entities/${entityId}/${kind}`, {
        object_type: 'ENTITY', case_id: data?.entity?.cases?.[0] || null,
        rationale: note || (kind === 'verify' ? 'Verified against supporting evidence.' : 'Insufficient support for this entity record.'),
      })
      notify('success', kind === 'verify' ? 'Entity human-verified' : 'Entity rejected',
        'The analytical finding is preserved; only its verification status changed.')
      setNote(''); await load(); onChanged?.()
    } catch (err) {
      notify('error', 'Action not permitted', err instanceof ApiError ? err.message : undefined)
    } finally { setBusy(null) }
  }

  async function annotate() {
    if (!entityId || !note.trim()) return
    setBusy('annotate')
    try {
      await api.post(`/api/entities/${entityId}/annotate`, { object_type: 'ENTITY', text: note.trim() })
      notify('success', 'Annotation recorded')
      setNote(''); await load()
    } catch (err) {
      notify('error', 'Annotation failed', err instanceof ApiError ? err.message : undefined)
    } finally { setBusy(null) }
  }

  if (!entityId) return null
  const e = data?.entity

  return (
    <aside className="glass flex h-full max-h-[calc(100vh-160px)] flex-col overflow-hidden">
      <header className="flex items-start justify-between gap-2 border-b border-[var(--color-border)] px-4 py-3">
        <div className="min-w-0">
          <p className="section-header !text-[11.5px]">Entity profile</p>
          <h3 className="truncate text-[16px] font-semibold text-[var(--color-primary-deep)]">{e?.label || entityId}</h3>
        </div>
        <button onClick={onClose} className="focus-ring rounded-lg p-1.5 text-[var(--color-text-muted)] transition hover:bg-[var(--color-primary-soft)]" aria-label="Close panel">
          <Icon name="close" size={16} />
        </button>
      </header>

      <div className="min-h-0 flex-1 space-y-4 overflow-y-auto px-4 py-4">
        {loading && <LoadingBlock label="Loading entity evidence…" rows={2} />}
        {error && <ErrorState message={error} onRetry={load} />}
        {e && (
          <>
            <div className="flex flex-wrap items-center gap-1.5">
              <Badge tone="navy">{e.entity_type}</Badge>
              <SupportBadge level={e.support_level} />
              <StatusPill status={e.verification_status} />
              {(e.cases || []).map((c: string) => <Badge key={c} tone="blue">{c}</Badge>)}
            </div>

            {/* ── A2 — WHY THIS NODE RANKS WHERE IT RANKS ─────────────── */}
            <section className="surface-solid px-3.5 py-3">
              <div className="flex items-center justify-between gap-2">
                <p className="section-header !text-[11.5px]">Why this entity ranks here</p>
                {structuralExplanation?.score && (
                  <span className="data-num rounded-md bg-[var(--color-primary-soft)] px-1.5 py-0.5 text-[11.5px] font-semibold text-[var(--color-primary-deep)]">
                    {structuralExplanation.score}
                  </span>
                )}
              </div>
              {structuralExplanation?.degree || structuralExplanation?.betweenness ? (
                <div className="mt-2 space-y-2">
                  {structuralExplanation?.degree && (
                    <p className="text-[12.5px] leading-relaxed text-[var(--color-text)]">{structuralExplanation.degree}</p>
                  )}
                  {structuralExplanation?.betweenness && structuralExplanation.betweenness !== structuralExplanation.degree && (
                    <p className="border-t border-[var(--color-border)] pt-2 text-[12.5px] leading-relaxed text-[var(--color-text-muted)]">
                      {structuralExplanation.betweenness}
                    </p>
                  )}
                </div>
              ) : analysisReady ? (
                <p className="mt-2 text-[12.5px] leading-relaxed text-[var(--color-text-muted)]">
                  This entity is not in the top structural ranks for the current scope, so no centrality
                  explanation is published for it. Its evidence-backed relationships are listed below.
                </p>
              ) : (
                <p className="mt-2 text-[12.5px] leading-relaxed text-[var(--color-text-muted)]">
                  Run the network analysis to see the structural (degree / betweenness) explanation for this entity.
                </p>
              )}
              {!analysisReady && onRunAnalysis && (
                <Button size="sm" variant="outline" className="mt-2.5 w-full" icon="spark" loading={analysing} onClick={onRunAnalysis}>
                  Run network analysis
                </Button>
              )}
            </section>

            <section className="surface-solid px-3.5 py-3">
              <KeyValue items={[
                ['Entity ID', <span key="id" className="mono-id">{e.entity_id}</span>],
                ['Normalized', <span key="n" className="mono-id">{e.normalized}</span>],
                ['Degree (connections)', <span key="d" className="data-num">{data.degree}</span>],
                ['Evidence items', <span key="ev" className="data-num">{(data.evidence || []).length}</span>],
                ['Identifier', e.identifier_masked
                  ? <MaskedValue key="m" value={e.label} entityId={e.entity_id} masked revealEndpoint={e.reveal_endpoint} />
                  : <span key="p" className="text-[12.5px] text-[var(--color-text-muted)]">not an identifier — shown in full</span>],
              ]} />
              {e.masking_policy && (
                <p className="mt-2.5 rounded-[10px] bg-[var(--color-primary-soft)] px-2.5 py-2 text-[11.5px] leading-relaxed text-[var(--color-text)]">
                  {e.masking_policy}
                </p>
              )}
            </section>

            {e.identifier_masked && (
              <section className="surface-solid px-3.5 py-3">
                <p className="section-header !text-[11.5px]">Identifier (masked)</p>
                <p className="mono-id mt-1.5 text-[13px] font-semibold text-[var(--color-text)]">
                  {revealed ? revealed.value : e.normalized}
                </p>
                {revealed ? (
                  <p className="mt-1.5 text-[11.5px] text-[var(--color-success)]">
                    Revealed · the access was written to the audit trail as IDENTIFIER_REVEALED.
                  </p>
                ) : (
                  <div className="mt-2 flex flex-wrap items-center gap-2">
                    <Button size="sm" icon="eye" loading={revealBusy} onClick={revealIdentifier}>
                      Reveal full identifier
                    </Button>
                    <span className="text-[11px] text-[var(--color-text-muted)]">
                      {e.masking_policy || 'Revealing is recorded and audited.'}
                    </span>
                  </div>
                )}
              </section>
            )}

            {e.attributes?.role_in_case && (
              <p className="surface-solid px-3 py-2 text-[12.5px] text-[var(--color-text)]">
                <span className="font-semibold">Role in case:</span> {e.attributes.role_in_case}
              </p>
            )}

            <Section title={`Relationships (${data.relationships.length})`}>
              {data.relationships.length === 0 && (
                <Empty text="No evidence-backed relationships recorded for this entity." />
              )}
              <ul className="space-y-1.5">
                {data.relationships.map((r: any) => (
                  <li key={r.relationship_id} className="surface-solid px-2.5 py-2">
                    <div className="flex flex-wrap items-center gap-1.5">
                      <EntityChip type="" label={r.direction === 'OUT' ? r.target_label : r.source_label}
                        onClick={() => onSelectEntity?.(r.direction === 'OUT' ? r.target : r.source)} />
                      <Badge tone="slate">{r.relationship_type}</Badge>
                      <SupportBadge level={r.support_level} />
                    </div>
                    <p className="mono-id mt-1.5 text-[11px] text-[var(--color-text-muted)]">
                      {r.timestamp?.slice(0, 16).replace('T', ' ')} · {r.evidence_id} · {r.source_document}
                    </p>
                  </li>
                ))}
              </ul>
            </Section>

            <Section title={`Supporting evidence (${(data.evidence || []).length})`}>
              {(data.evidence || []).length === 0 && <Empty text="No evidence linked to this entity yet." />}
              <ul className="space-y-1.5">
                {(data.evidence || []).map((ev: any) => (
                  <li key={ev.evidence_id} className="surface-solid flex flex-wrap items-center justify-between gap-1.5 px-2.5 py-2">
                    <span className="mono-id text-[12px] font-semibold text-[var(--color-text)]">{ev.evidence_id} · {ev.type}</span>
                    <span className="flex items-center gap-1">
                      <StatusPill status={ev.integrity_status} />
                      <StatusPill status={ev.verification_status} />
                    </span>
                  </li>
                ))}
              </ul>
            </Section>

            <Section title={`Timeline (${(data.timeline || []).length})`}>
              {(data.timeline || []).length === 0 && <Empty text="No timestamped events reference this entity." />}
              <ol className="space-y-2 border-l-2 border-[var(--color-primary-soft)] pl-3">
                {(data.timeline || []).map((t: any) => (
                  <li key={t.event_id} className="relative">
                    <span className="absolute -left-[17px] top-1.5 h-2 w-2 rounded-full bg-[var(--color-primary)]" />
                    <p className="text-[12.5px] font-semibold text-[var(--color-text)]">{t.title}</p>
                    <p className="mono-id text-[11px] text-[var(--color-text-muted)]">
                      {t.timestamp?.replace('T', ' ').replace('Z', '')} · {t.case_id} · {t.evidence_id || 'no evidence ref'}
                    </p>
                  </li>
                ))}
              </ol>
            </Section>

            <Section title="Human validation">
              <TextArea value={note} onChange={(ev) => setNote(ev.target.value)}
                placeholder="Rationale or investigator annotation (recorded in the audit trail)…" className="min-h-[70px]" />
              <div className="mt-2 flex flex-wrap gap-2">
                <Button size="sm" variant="success" icon="check" loading={busy === 'verify'}
                  disabled={!can('verification:decide')} onClick={() => decide('verify')}>Verify</Button>
                <Button size="sm" variant="danger" icon="reject" loading={busy === 'reject'}
                  disabled={!can('verification:decide')} onClick={() => decide('reject')}>Reject</Button>
                <Button size="sm" icon="note" loading={busy === 'annotate'}
                  disabled={!can('entity:annotate') || !note.trim()} onClick={annotate}>Annotate</Button>
              </div>
              {!can('verification:decide') && (
                <p className="mt-2 text-[11.5px] text-[var(--color-text-muted)]">
                  Your role may annotate and submit findings; verification decisions are reserved for supervisors.
                </p>
              )}
              {(data.annotations || []).length > 0 && (
                <ul className="mt-3 space-y-1.5">
                  {data.annotations.map((a: any) => (
                    <li key={a.annotation_id} className="surface-solid px-2.5 py-2 text-[12px] text-[var(--color-text)]">
                      <span className="font-semibold">{a.author}</span> · {a.timestamp?.replace('T', ' ').replace('Z', '')}
                      <p className="mt-0.5">{a.text}</p>
                    </li>
                  ))}
                </ul>
              )}
            </Section>

            <p className="surface-solid px-3 py-2 text-[11.5px] leading-relaxed text-[var(--color-text-muted)]">
              {data.safety_note}
            </p>
          </>
        )}
      </div>
    </aside>
  )
}

export function RelationshipPanel({
  relationshipId, onClose, onChanged,
}: { relationshipId: string | null; onClose: () => void; onChanged?: () => void }) {
  const { can, notify } = useApp()
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState<string | null>(null)

  async function load() {
    if (!relationshipId) return
    setLoading(true); setError(null)
    try { setData(await api.get<any>(`/api/relationships/${relationshipId}`)) }
    catch (err) { setError(err instanceof ApiError ? err.message : 'Relationship could not be loaded.') }
    finally { setLoading(false) }
  }
  useEffect(() => { setData(null); load() /* eslint-disable-next-line */ }, [relationshipId])

  async function decide(kind: 'verify' | 'reject') {
    if (!relationshipId) return
    setBusy(kind)
    try {
      await api.post(`/api/relationships/${relationshipId}/${kind}`, {
        object_type: 'RELATIONSHIP', case_id: data?.relationship?.case_id,
        rationale: note || (kind === 'verify' ? 'Relationship corroborated by cited evidence.' : 'Support insufficient for this relationship.'),
      })
      notify('success', kind === 'verify' ? 'Relationship human-verified' : 'Relationship rejected',
        'Original analytical finding retained for audit.')
      setNote(''); await load(); onChanged?.()
    } catch (err) {
      notify('error', 'Action not permitted', err instanceof ApiError ? err.message : undefined)
    } finally { setBusy(null) }
  }

  if (!relationshipId) return null
  const r = data?.relationship

  return (
    <aside className="glass flex h-full max-h-[calc(100vh-160px)] flex-col overflow-hidden">
      <header className="flex items-start justify-between gap-2 border-b border-[var(--color-border)] px-4 py-3">
        <div className="min-w-0">
          <p className="section-header !text-[11.5px]">Relationship details</p>
          <h3 className="truncate text-[14.5px] font-semibold text-[var(--color-primary-deep)]">
            {r ? `${r.source_entity?.label} → ${r.target_entity?.label}` : relationshipId}
          </h3>
        </div>
        <button onClick={onClose} className="focus-ring rounded-lg p-1.5 text-[var(--color-text-muted)] transition hover:bg-[var(--color-primary-soft)]" aria-label="Close panel">
          <Icon name="close" size={16} />
        </button>
      </header>
      <div className="min-h-0 flex-1 space-y-4 overflow-y-auto px-4 py-4">
        {loading && <LoadingBlock label="Loading relationship evidence…" rows={2} />}
        {error && <ErrorState message={error} onRetry={load} />}
        {r && (
          <>
            <div className="flex flex-wrap gap-1.5">
              <Badge tone="navy">{r.relationship_type}</Badge>
              <SupportBadge level={r.support_level} />
              <StatusPill status={r.verification_status} />
              <Badge tone="blue">{r.case_id}</Badge>
            </div>

            {/* a candidate relationship must read as unconfirmed, not as a settled fact */}
            {String(r.verification_status || '').toUpperCase().includes('CANDIDATE') && (
              <p className="w-full rounded-[12px] border border-dashed border-[var(--color-warning)] px-3 py-2 text-[12px] leading-relaxed text-[var(--color-warning)]">
                Candidate link — <span className="mono-id">{r.relationship_id}</span> is an analytical association between
                two entities in the evidence. It is not a confirmed fact and is not evidence of any offence.
              </p>
            )}

            <section className="surface-solid px-3.5 py-3">
              <KeyValue items={[
                ['Source entity', `${r.source_entity?.label} (${r.source_entity?.entity_type})`],
                ['Target entity', `${r.target_entity?.label} (${r.target_entity?.entity_type})`],
                ['Date', <span key="d" className="mono-id">{r.timestamp?.replace('T', ' ').replace('Z', '')}</span>],
                ['Evidence', <span key="e" className="mono-id">{r.evidence_id}</span>],
                ['Source document', r.source_document],
                ['Relationship ID', <span key="r" className="mono-id">{r.relationship_id}</span>],
              ]} />
              {r.notes && <p className="mt-3 rounded-[10px] bg-[var(--color-primary-soft)] px-3 py-2 text-[12.5px] text-[var(--color-text)]">{r.notes}</p>}
            </section>

            {data.evidence && (
              <Section title="Supporting evidence">
                <div className="surface-solid px-3 py-2.5">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="mono-id text-[12.5px] font-semibold text-[var(--color-text)]">{data.evidence.evidence_id}</span>
                    <span className="flex gap-1">
                      <StatusPill status={data.evidence.integrity_status} />
                      <StatusPill status={data.evidence.verification_status} />
                    </span>
                  </div>
                  <p className="mt-1 text-[12px] text-[var(--color-text-muted)]">
                    {data.evidence.type} · {data.evidence.source} · {data.evidence.timestamp?.replace('T', ' ').replace('Z', '')}
                  </p>
                  <p className="mt-1.5"><Hash value={data.evidence.sha256} chars={24} /></p>
                  {data.evidence.source_trust && (
                    <p className="mt-2 flex items-center gap-2">
                      <SourceTrustBadge trust={data.evidence.source_trust} weight={data.evidence.source_trust_weight} />
                      <span className="text-[11px] text-[var(--color-text-muted)]">{data.evidence.source_trust_explanation}</span>
                    </p>
                  )}
                </div>
              </Section>
            )}

            <Section title="Human validation">
              <TextArea value={note} onChange={(e) => setNote(e.target.value)} placeholder="Verification rationale…" className="min-h-[64px]" />
              <div className="mt-2 flex flex-wrap gap-2">
                <Button size="sm" variant="success" icon="check" loading={busy === 'verify'}
                  disabled={!can('verification:decide')} onClick={() => decide('verify')}>Verify</Button>
                <Button size="sm" variant="danger" icon="reject" loading={busy === 'reject'}
                  disabled={!can('verification:decide')} onClick={() => decide('reject')}>Reject</Button>
              </div>
              {!can('verification:decide') && (
                <p className="mt-2 text-[11.5px] text-[var(--color-text-muted)]">
                  Verification decisions are reserved for supervisors; your role can annotate this relationship.
                </p>
              )}
            </Section>
          </>
        )}
      </div>
    </aside>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      {/* drawer-local section head: same muted token, sized for a 380px rail */}
      <h2 className="section-header mb-2 !text-[12.5px]">{title}</h2>
      {children}
    </div>
  )
}

function Empty({ text }: { text: string }) {
  return (
    <p className="rounded-[12px] border border-dashed border-[var(--color-border)] bg-[var(--color-surface-solid)] px-3 py-2 text-[12.5px] text-[var(--color-text-muted)]">
      {text}
    </p>
  )
}
