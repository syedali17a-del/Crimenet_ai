import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useApp } from '../state/AppContext'
import { useFetch } from '../hooks/useFetch'
import { api, ApiError } from '../services/api'
import { Icon } from '../components/shared/Icon'
import {
  Badge, Button, Card, EmptyState, ErrorState, Field, Hash, LoadingBlock,
  Modal, PageHeader, ProvenanceStrip, SectionHeader, Select, SourceTrustBadge, StatusPill,
  SupportBadge, Td, TextArea, TextInput, Th,
} from '../components/shared/ui'
import type { EvidenceItem } from '../types'
import { useI18n } from '../i18n/LanguageContext'

/* ============================================================================
   EVIDENCE WORKSPACE
   The registry table and the document reading panel are SOLID surfaces: this is
   the densest text in the product and blurred glass would hurt it. Glass is used
   only for the provenance strip above the reading panel (short labels, high
   contrast) and for the register-evidence modal.

   Identifiers and hashes are monospace + tabular so they can be read character
   by character and compared against a printed record.
   ============================================================================ */

const TYPES = ['FIR', 'POLICE_REPORT', 'CDR', 'FINANCIAL_RECORD', 'SURVEILLANCE_REPORT', 'INTELLIGENCE_REPORT', 'IMAGE', 'PDF', 'CSV']
const PIPELINE = ['UPLOADED', 'PROCESSING', 'EXTRACTED', 'ENTITIES_FOUND', 'RELATIONSHIPS_CANDIDATE']
const MASKABLE_ENTITIES = ['PHONE', 'ACCOUNT', 'DEVICE']

export default function Evidence() {
  const { t, tok, fmt } = useI18n()
  const { cases, activeCase, can, notify } = useApp()
  const [params, setParams] = useSearchParams()
  const focus = params.get('focus')
  const caseFilter = params.get('case') || activeCase || ''

  const list = useFetch<EvidenceItem[]>(`/api/evidence${caseFilter ? `?case_id=${caseFilter}` : ''}`, [caseFilter])
  const [selected, setSelected] = useState<string | null>(focus)
  const [uploadOpen, setUploadOpen] = useState(false)
  const [typeFilter, setTypeFilter] = useState('')
  const [busy, setBusy] = useState<string | null>(null)
  const [support, setSupport] = useState<any>(null)
  const [supportBusy, setSupportBusy] = useState(false)

  useEffect(() => { if (focus) setSelected(focus) }, [focus])
  useEffect(() => { setSupport(null) }, [selected])

  const rows = useMemo(
    () => (list.data || []).filter((e) => !typeFilter || e.evidence_type === typeFilter),
    [list.data, typeFilter],
  )

  const detail = useFetch<any>(selected ? `/api/evidence/${selected}` : null, [selected])

  async function act(kind: 'process' | 'integrity-check' | 'verify' | 'reject', id: string, body?: unknown) {
    setBusy(id + kind)
    try {
      const res = await api.post<any>(`/api/evidence/${id}/${kind}`, body ?? {})
      if (kind === 'process') {
        notify('success', `${id}: document pipeline complete`,
          `${res.extraction?.entities?.length ?? 0} entities · ${res.graph_updates?.relationships?.length ?? 0} candidate relationships`)
      } else if (kind === 'integrity-check') {
        notify(res.status === 'VERIFIED' ? 'success' : 'error', `${id}: ${res.status}`, res.message)
      } else {
        notify('success', `${id} ${kind === 'verify' ? 'human-verified' : 'rejected'}`, 'Recorded in audit trail and ledger.')
      }
      list.reload(); if (selected === id) detail.reload()
    } catch (err) {
      notify('error', 'Action failed', err instanceof ApiError ? err.message : undefined)
    } finally { setBusy(null) }
  }

  /** A7 — ask the same weighting function the corroboration engine uses. */
  async function checkSupport() {
    if (!selected) return
    setSupportBusy(true)
    try {
      setSupport(await api.post<any>('/api/analysis/evidence-support', { evidence_ids: [selected] }))
    } catch (err) {
      notify('error', 'Could not compute corroboration weight', err instanceof ApiError ? err.message : undefined)
    } finally { setSupportBusy(false) }
  }

  const ev = detail.data?.evidence

  return (
    <>
      <PageHeader
        tagline={t.pages.evidence.tagline}
        title={t.pages.evidence.title}
        description={t.pages.evidence.description}
      >
        <Select value={caseFilter} onChange={(e) => setParams(e.target.value ? { case: e.target.value } : {})} className="w-48">
          <option value="">{t.evidence.allAuthorizedCases}</option>
          {cases.map((c) => <option key={c.case_id} value={c.case_id}>{c.case_id}</option>)}
        </Select>
        <Button icon="refresh" onClick={list.reload}>{t.evidence.refresh}</Button>
        {can('evidence:upload') && (
          <Button variant="primary" icon="upload" onClick={() => setUploadOpen(true)}>{t.evidence.upload}</Button>
        )}
      </PageHeader>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-[1.3fr_1fr]">
        {/* ── registry table (solid surface) ─────────────────────────────── */}
        <section className="surface-solid self-start">
          <header className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--color-border)] px-5 py-3.5">
            <div className="flex items-center gap-2">
              <span className="text-[var(--color-primary)]"><Icon name="evidence" size={16} /></span>
              <h2 className="section-header !text-[13px]">{t.evidence.itemsTitle(rows.length)}</h2>
            </div>
            <Select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)} className="w-44">
              <option value="">{t.evidence.allTypes}</option>
              {TYPES.map((et) => <option key={et} value={et}>{tok(t.tokens.evidenceType, et)}</option>)}
            </Select>
          </header>
          <div className="p-5">
            {list.loading && <LoadingBlock label={t.evidence.loading} variant="table" />}
            {list.error && <ErrorState message={list.error} onRetry={list.reload} />}
            {!list.loading && rows.length === 0 && (
              <EmptyState title={t.evidence.noneInScope} message={t.evidence.noneInScopeGap} icon="evidence"
                action={can('evidence:upload')
                  ? <Button size="sm" variant="primary" icon="upload" onClick={() => setUploadOpen(true)}>{t.evidence.upload}</Button>
                  : undefined} />
            )}
            {rows.length > 0 && (
              <div className="-mx-5 overflow-x-auto">
                <table className="w-full min-w-[680px] border-collapse text-left text-[13px]">
                  <thead>
                    <tr>
                      <Th>{t.evidence.thEvidence}</Th><Th>{t.evidence.thTypeSource}</Th><Th>{t.evidence.thCase}</Th>
                      <Th>{t.evidence.thProcessing}</Th><Th>{t.evidence.thIntegrity}</Th><Th>{t.evidence.thHash}</Th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((e) => {
                      const active = selected === e.evidence_id
                      return (
                        <tr
                          key={e.evidence_id}
                          onClick={() => setSelected(e.evidence_id)}
                          className={`cursor-pointer transition ${active ? 'bg-[var(--color-primary-soft)]' : 'hover:bg-[var(--color-primary-soft)]/50'}`}
                        >
                          <Td className="border-l-2" >
                            <span className="flex items-start gap-2">
                              <span className={`mt-1 h-3 w-[3px] shrink-0 rounded ${active ? 'bg-[var(--color-primary)]' : 'bg-transparent'}`} />
                              <span>
                                <span className="mono-id font-semibold text-[var(--color-primary-deep)]">{e.evidence_id}</span>
                                <br /><span className="text-[11px] text-[var(--color-text-muted)]">{fmt.dateTime(e.timestamp)}</span>
                              </span>
                            </span>
                          </Td>
                          <Td>
                            {tok(t.tokens.evidenceType, e.evidence_type)}
                            <br /><span className="text-[11px] text-[var(--color-text-muted)]">{e.source}</span>
                          </Td>
                          <Td><span className="mono-id">{e.case_id}</span></Td>
                          <Td><StatusPill status={e.processing_status} /></Td>
                          <Td><StatusPill status={e.integrity_status} /></Td>
                          <Td><Hash value={e.sha256} chars={10} /></Td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </section>

        {/* ── detail column ─────────────────────────────────────────────── */}
        <div className="space-y-5">
          {!selected && (
            <Card title={t.evidence.detailTitle} icon="doc" solid>
              <EmptyState title={t.evidence.detailEmpty} icon="search"
                message="Select a row in the registry to open its content, extraction and chain of custody." />
            </Card>
          )}

          {selected && detail.loading && (
            <Card title={t.evidence.detailTitle} icon="doc" solid><LoadingBlock rows={3} variant="table" /></Card>
          )}
          {selected && detail.error && (
            <Card title={t.evidence.detailTitle} icon="doc" solid><ErrorState message={detail.error} onRetry={detail.reload} /></Card>
          )}

          {selected && ev && (
            <>
              {/* glass provenance strip — short labels only, never body copy */}
              <ProvenanceStrip
                items={[
                  ['Evidence ID', <span key="id" className="mono-id font-semibold">{ev.evidence_id}</span>],
                  [t.common.type, tok(t.tokens.evidenceType, ev.evidence_type)],
                  [t.common.source, ev.source],
                  [t.common.case, <span key="c" className="mono-id">{ev.case_id}</span>],
                  ['SHA-256', <Hash key="h" value={ev.sha256} chars={20} />],
                  [t.common.status, <StatusPill key="s" status={ev.integrity_status} />],
                ]}
              />

              <section className="surface-solid">
                <header className="flex flex-wrap items-start justify-between gap-3 border-b border-[var(--color-border)] px-5 py-3.5">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-[var(--color-primary)]"><Icon name="doc" size={16} /></span>
                      <h2 className="section-header !text-[13px]">
                        {tok(t.tokens.evidenceType, ev.evidence_type)} · <span className="mono-id">{ev.evidence_id}</span>
                      </h2>
                    </div>
                    <p className="mt-1 text-[12.5px] text-[var(--color-text-muted)]">{ev.source} · <span className="mono-id">{ev.case_id}</span></p>
                  </div>
                  <Button size="sm" icon="close" onClick={() => setSelected(null)}>{t.common.close}</Button>
                </header>

                <div className="space-y-5 p-5">
                  <div className="flex flex-wrap items-center gap-1.5">
                    <StatusPill status={ev.integrity_status} />
                    <StatusPill status={ev.verification_status} />
                    <StatusPill status={ev.processing_status} />
                    <Badge tone="slate">{ev.text_origin.replace(/_/g, ' ')}</Badge>
                    {/* honest OCR state — never claim OCR ran when it did not */}
                    <span className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide ${
                      ev.ocr_applied ? 'status-verified' : 'status-candidate'
                    }`}>
                      <Icon name={ev.ocr_applied ? 'check' : 'info'} size={11} />
                      {ev.ocr_applied ? t.evidence.ocrApplied : t.evidence.ocrNotApplied}
                    </span>
                    {ev.source_trust && (
                      <SourceTrustBadge trust={ev.source_trust} weight={ev.source_trust_weight} />
                    )}
                  </div>

                  {/* processing pipeline trace */}
                  <div>
                    <SectionHeader>{t.evidence.processingPipeline}</SectionHeader>
                    <div className="flex flex-wrap items-center gap-1">
                      {PIPELINE.map((stage, i) => {
                        const reached = PIPELINE.indexOf(ev.processing_status) >= i
                        return (
                          <span key={stage} className="flex items-center gap-1">
                            <span className={`rounded-md px-2 py-1 text-[11px] font-semibold ${
                              reached
                                ? 'bg-[var(--color-primary)] text-white'
                                : 'border border-[var(--color-border)] bg-[var(--color-surface-solid)] text-[var(--color-text-muted)]'
                            }`}>
                              {tok(t.tokens.processingStatus, stage)}
                            </span>
                            {i < PIPELINE.length - 1 && <span className="text-[var(--color-text-muted)]">›</span>}
                          </span>
                        )
                      })}
                    </div>
                    <p className="mt-2 flex flex-wrap items-center gap-2 text-[12px] text-[var(--color-text-muted)]">
                      {t.evidence.registeredHash} <Hash value={ev.sha256} chars={32} />
                    </p>
                  </div>

                  {/* actions — every button performs a real, audited operation */}
                  <div className="flex flex-wrap gap-2">
                    {can('evidence:process') && (
                      <Button size="sm" icon="spark" loading={busy === selected + 'process'} onClick={() => act('process', selected)}>
                        {t.evidence.processDocument}
                      </Button>
                    )}
                    {can('evidence:integrity') && (
                      <Button size="sm" icon="hash" loading={busy === selected + 'integrity-check'} onClick={() => act('integrity-check', selected)}>
                        {t.evidence.integrityCheck}
                      </Button>
                    )}
                    {can('analysis:run') && (
                      <Button size="sm" icon="shield" loading={supportBusy} onClick={checkSupport}>
                        Corroboration weight
                      </Button>
                    )}
                    {can('verification:decide') && (
                      <>
                        <Button size="sm" variant="success" icon="check" loading={busy === selected + 'verify'}
                          onClick={() => act('verify', selected, { object_type: 'EVIDENCE', rationale: t.evidence.verifyRationale })}>{t.evidence.verify}</Button>
                        <Button size="sm" variant="danger" icon="reject" loading={busy === selected + 'reject'}
                          onClick={() => act('reject', selected, { object_type: 'EVIDENCE', rationale: t.evidence.rejectRationale })}>{t.evidence.reject}</Button>
                      </>
                    )}
                  </div>

                  {/* A7 corroboration weighting, computed live by the backend */}
                  {support && (
                    <div className="rounded-[12px] border border-[var(--color-border)] bg-[var(--color-primary-soft)] px-3.5 py-3">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <p className="section-header !text-[11.5px]">Source trust &amp; corroboration weight</p>
                        <SupportBadge level={support.support_level_reachable} />
                      </div>
                      <p className="data-num mt-2 text-[12.5px] text-[var(--color-text)]">
                        Weighted support {support.weighted_support?.toFixed?.(2) ?? support.weighted_support} from{' '}
                        {support.independent_sources} independent source(s).
                      </p>
                      <p className="mt-1 text-[12.5px] leading-relaxed text-[var(--color-text)]">{support.explanation}</p>
                      <ul className="mt-2 space-y-1">
                        {(support.sources || []).map((s: any) => (
                          <li key={s.source} className="flex flex-wrap items-center gap-2 text-[11.5px] text-[var(--color-text)]">
                            <SourceTrustBadge trust={s.source_trust} weight={s.weight} />
                            <span>{s.source}</span>
                            <span className="mono-id text-[var(--color-text-muted)]">{s.evidence_ids.join(', ')}</span>
                          </li>
                        ))}
                      </ul>
                      <p className="mt-2 text-[11px] leading-relaxed text-[var(--color-text-muted)]">{support.policy_note}</p>
                    </div>
                  )}

                  {ev.notes && (
                    <p className="flex items-start gap-2 rounded-[12px] border border-[var(--color-warning)] bg-[rgba(184,121,26,0.07)] px-3 py-2 text-[12.5px] text-[var(--color-text)]">
                      <Icon name="info" size={13} /> {ev.notes}
                    </p>
                  )}
                </div>
              </section>

              {/* reading panel — the document itself, on solid, generous type */}
              <section className="surface-solid">
                <header className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--color-border)] px-5 py-3.5">
                  <h2 className="section-header !text-[13px]">{t.evidence.extractedContent}</h2>
                  <span className="data-num text-[11.5px] text-[var(--color-text-muted)]">
                    {t.evidence.charactersInStorage(detail.data.content_length)}
                  </span>
                </header>
                <div className="p-5">
                  {detail.data.content_preview ? (
                    <div className="reading-panel max-h-[380px] overflow-auto whitespace-pre-wrap">{detail.data.content_preview}</div>
                  ) : (
                    <EmptyState title={t.evidence.noTextContent} icon="doc" />
                  )}
                </div>
              </section>

              {/* extraction */}
              {detail.data.extraction && (
                <section className="surface-solid">
                  <header className="border-b border-[var(--color-border)] px-5 py-3.5">
                    <h2 className="section-header !text-[13px]">
                      {t.evidence.entitiesExtracted((Object.values(detail.data.extraction.counts || {}) as number[]).reduce((a, b) => a + b, 0))}
                    </h2>
                  </header>
                  <div className="p-5">
                    <div className="flex flex-wrap gap-1.5">
                      {(detail.data.extraction.entities || []).map((e: any, i: number) => {
                        const mono = MASKABLE_ENTITIES.includes(e.entity_type)
                        return (
                          <span key={i} className="inline-flex items-center gap-1.5 rounded-md border border-[var(--color-border)] bg-[var(--color-surface-solid)] px-2 py-1 text-[11.5px]">
                            <span className={`font-semibold text-[var(--color-text)] ${mono ? 'mono-id' : ''}`}>{e.surface}</span>
                            <span className="text-[10px] font-semibold uppercase tracking-wide text-[var(--color-primary)]">
                              {tok(t.tokens.entityType, e.entity_type)}
                            </span>
                          </span>
                        )
                      })}
                    </div>
                    <p className="mt-3 text-[11.5px] text-[var(--color-text-muted)]">
                      {t.evidence.nerBackend}: {detail.data.extraction.backend?.ner_backend} · {detail.data.extraction.backend?.rule_layer}
                    </p>
                    <p className="mt-1 text-[11.5px] leading-relaxed text-[var(--color-text-muted)]">
                      Extracted surfaces are quoted from this document. Structured PHONE / ACCOUNT / DEVICE
                      identifiers are masked wherever they are presented as graph entities; the document text
                      itself stays readable because that is what an investigator has to read.
                    </p>
                  </div>
                </section>
              )}

              {/* chain of custody */}
              <section className="surface-solid">
                <header className="border-b border-[var(--color-border)] px-5 py-3.5">
                  <h2 className="section-header !text-[13px]">{t.evidence.provenance}</h2>
                </header>
                <div className="p-5">
                  <ol className="space-y-3 border-l-2 border-[var(--color-primary-soft)] pl-4">
                    {(ev.provenance || []).map((p: any, i: number) => (
                      <li key={i} className="relative">
                        <span className="absolute -left-[22px] top-1.5 h-2.5 w-2.5 rounded-full border-2 border-[var(--color-surface-solid)] bg-[var(--color-primary)]" />
                        <p className="text-[12.5px] font-semibold text-[var(--color-text)]">{p.step}</p>
                        <p className="text-[11.5px] text-[var(--color-text-muted)]">{fmt.dateTime(p.timestamp)} · {p.actor}</p>
                        <p className="text-[12px] text-[var(--color-text)]">{p.detail}</p>
                      </li>
                    ))}
                  </ol>
                  {(detail.data.ledger || []).length > 0 && (
                    <div className="mt-4">
                      <SectionHeader>{t.evidence.ledgerAnchors}</SectionHeader>
                      <ul className="space-y-1.5">
                        {detail.data.ledger.map((b: any) => (
                          <li key={b.index} className="flex flex-wrap items-center gap-2 rounded-[10px] border border-[var(--color-border)] px-2.5 py-1.5 text-[11.5px]">
                            <Badge tone="navy">#{b.index}</Badge>
                            <span className="font-semibold text-[var(--color-text)]">{tok(t.tokens.eventType, b.event_type)}</span>
                            <span className="text-[var(--color-text-muted)]">{fmt.dateTime(b.timestamp)}</span>
                            <Hash value={b.block_hash} chars={12} />
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </section>
            </>
          )}

          {selected && !detail.loading && !detail.error && (detail.data?.related_relationships || []).length > 0 && (
            <Card solid title={t.analysis.net.graphTitle} icon="network" subtitle={`${detail.data.related_relationships.length} candidate relationship(s) generated from this document`}>
              <ul className="space-y-1.5">
                {detail.data.related_relationships.map((r: any) => (
                  <li key={r.id} className="rounded-[10px] border border-[var(--color-border)] px-3 py-2">
                    <p className="text-[12.5px] font-semibold text-[var(--color-text)]">
                      {r.source_label} → {r.target_label}
                    </p>
                    <div className="mt-1 flex flex-wrap items-center gap-1.5 text-[11.5px] text-[var(--color-text-muted)]">
                      <Badge tone="slate">{tok(t.tokens.relationshipType, r.rel_type)}</Badge>
                      <StatusPill status={r.verification_status} />
                      <span className="mono-id">{r.id}</span>
                    </div>
                  </li>
                ))}
              </ul>
              <p className="mt-3 text-[11.5px] leading-relaxed text-[var(--color-text-muted)]">
                These are analytical candidates, not confirmed facts. A link becomes VERIFIED only after a
                supervisor records a decision; nothing is merged automatically.
              </p>
            </Card>
          )}
        </div>
      </div>

      <UploadModal open={uploadOpen} onClose={() => setUploadOpen(false)} defaultCase={caseFilter || cases[0]?.case_id || ''}
        onDone={() => { setUploadOpen(false); list.reload() }} />
    </>
  )
}

function UploadModal({ open, onClose, defaultCase, onDone }: { open: boolean; onClose: () => void; defaultCase: string; onDone: () => void }) {
  const { t, tok } = useI18n()
  const { cases, notify } = useApp()
  const [mode, setMode] = useState<'sample' | 'text' | 'file'>('sample')
  const [caseId, setCaseId] = useState(defaultCase)
  const [type, setType] = useState('FIR')
  const [source, setSource] = useState('Police Report')
  const [declaredTrust, setDeclaredTrust] = useState('OFFICER_UPLOAD')
  const [text, setText] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => { setCaseId(defaultCase) }, [defaultCase])

  async function submit() {
    setErr(null)
    if (!caseId) { setErr('Select the case this evidence belongs to.'); return }
    if (mode === 'text' && text.trim().length < 20) { setErr('Provide at least 20 characters of evidence text.'); return }
    if (mode === 'file' && !file) { setErr('Choose a file to upload.'); return }
    setBusy(true)
    try {
      let created: any
      if (mode === 'file' && file) {
        const form = new FormData()
        form.append('case_id', caseId); form.append('evidence_type', type)
        form.append('source', source || file.name); form.append('notes', 'Uploaded via evidence workspace')
        form.append('source_trust', declaredTrust)
        form.append('file', file)
        created = await api.upload<any>('/api/evidence/upload', form)
      } else {
        created = await api.post<any>('/api/evidence', {
          case_id: caseId, evidence_type: type, source,
          text_content: mode === 'text' ? text : undefined,
          use_synthetic_sample: mode === 'sample',
          source_trust: declaredTrust,
        })
      }
      notify('success', `Evidence ${created.evidence_id} registered`, 'SHA-256 computed and anchored to the ledger.')
      try {
        await api.post(`/api/evidence/${created.evidence_id}/process`, {})
        notify('info', t.evidence.processedToast(created.evidence_id), t.evidence.processedToastBody)
      } catch { /* processing permission may be absent; registration still succeeded */ }
      onDone()
    } catch (error) {
      setErr(error instanceof ApiError ? error.message : t.evidence.registerFailed)
    } finally { setBusy(false) }
  }

  return (
    <Modal open={open} onClose={onClose} title={t.evidence.registerTitle}
      subtitle={t.evidence.registerSubtitle}
      footer={
        <>
          <Button size="sm" onClick={onClose}>{t.evidence.cancel}</Button>
          <Button size="sm" variant="primary" icon="upload" loading={busy} onClick={submit}>{t.evidence.registerAndProcess}</Button>
        </>
      }>
      <div className="space-y-4">
        <div className="flex flex-wrap gap-2">
          {(['sample', 'text', 'file'] as const).map((m) => (
            <button key={m} onClick={() => setMode(m)} aria-pressed={mode === m}
              className={`focus-ring rounded-[10px] px-3 py-1.5 text-[12.5px] font-semibold transition ${
                mode === m
                  ? 'bg-[var(--color-primary)] text-white'
                  : 'border border-[var(--color-border)] bg-[var(--color-surface-solid)] text-[var(--color-text)] hover:border-[var(--color-primary)]'
              }`}>
              {m === 'sample' ? t.evidence.modeSample : m === 'text' ? t.evidence.modeText : t.evidence.modeFile}
            </button>
          ))}
        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <Field label={t.evidence.fieldCase} required>
            <Select value={caseId} onChange={(e) => setCaseId(e.target.value)}>
              <option value="">{t.evidence.selectCase}</option>
              {cases.map((c) => <option key={c.case_id} value={c.case_id}>{c.case_id} — {c.title}</option>)}
            </Select>
          </Field>
          <Field label={t.evidence.fieldEvidenceType} required>
            <Select value={type} onChange={(e) => setType(e.target.value)}>
              {TYPES.map((et) => <option key={et} value={et}>{tok(t.tokens.evidenceType, et)}</option>)}
            </Select>
          </Field>
          <Field label={t.evidence.fieldSource}>
            <TextInput value={source} onChange={(e) => setSource(e.target.value)} placeholder={t.evidence.fieldSourcePlaceholder} />
          </Field>
          <Field label="Source trust (declared provenance)"
            hint="Weights how much this document can corroborate on its own: officer 1.00 · bulk 0.60 · external 0.35.">
            <Select value={declaredTrust} onChange={(e) => setDeclaredTrust(e.target.value)}>
              <option value="OFFICER_UPLOAD">OFFICER_UPLOAD (1.00)</option>
              <option value="BULK_IMPORT">BULK_IMPORT (0.60)</option>
              <option value="EXTERNAL_SUBMISSION">EXTERNAL_SUBMISSION (0.35)</option>
            </Select>
          </Field>
        </div>

        {mode === 'text' && (
          <Field label={t.evidence.fieldText} hint={t.evidence.fieldTextHint}>
            <TextArea value={text} onChange={(e) => setText(e.target.value)} className="min-h-[130px]"
              placeholder={t.evidence.fieldTextPlaceholder} />
          </Field>
        )}

        {mode === 'file' && (
          <Field label={t.evidence.fieldFile} hint={t.evidence.fieldFileHint}>
            <input type="file" onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="focus-ring w-full rounded-[10px] border border-[var(--color-border)] bg-[var(--color-surface-solid)] px-3 py-2 text-[13px] file:mr-3 file:rounded-md file:border-0 file:bg-[var(--color-primary)] file:px-3 file:py-1.5 file:text-[12px] file:font-semibold file:text-white" />
          </Field>
        )}

        {mode === 'sample' && (
          <p className="rounded-[12px] border border-[var(--color-primary)] bg-[var(--color-primary-soft)] px-3 py-2 text-[12.5px] text-[var(--color-text)]">
            {t.evidence.sampleNoteA} <span className="font-semibold">{tok(t.tokens.evidenceType, type)}</span> {t.evidence.sampleNoteB}
          </p>
        )}

        <p className="rounded-[12px] border border-dashed border-[var(--color-text-muted)] px-3 py-2 text-[12px] leading-relaxed text-[var(--color-text-muted)]">
          Registration is immutable: the SHA-256 is computed on upload and the record is anchored to the
          permissioned ledger. Rejecting an item later changes its verification status — the original finding
          and its hash are never deleted.
        </p>

        {err && (
          <p className="rounded-[12px] border border-[var(--color-danger)] bg-[rgba(196,52,31,0.06)] px-3 py-2 text-[12.5px] text-[var(--color-danger)]">{err}</p>
        )}
      </div>
    </Modal>
  )
}
