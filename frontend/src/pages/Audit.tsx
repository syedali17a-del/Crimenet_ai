import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApp } from '../state/AppContext'
import { useFetch } from '../hooks/useFetch'
import { api, ApiError } from '../services/api'
import { Icon } from '../components/shared/Icon'
import {
  Button, Card, EmptyState, ErrorState, Hash, LoadingBlock, PageHeader, SectionHeader,
  Select, StatusPill, TextInput,
} from '../components/shared/ui'
import { useI18n } from '../i18n/LanguageContext'

/* ============================================================================
   AUDIT & INTEGRITY
   The evidentiary record. Austere by design: monochrome surfaces, no decorative
   colour, colour only where it signals a mismatch or a verification decision.
   Every table is dense, solid and monospace for identifiers and hashes, because
   this is the surface an auditor reads line by line.
   ============================================================================ */

const TABS = [
  { id: 'audit', label: 'Audit trail', icon: 'audit' as const },
  { id: 'integrity', label: 'Evidence integrity', icon: 'shield' as const },
  { id: 'ledger', label: 'Permissioned ledger', icon: 'hash' as const },
  { id: 'verifications', label: 'Human decisions', icon: 'check' as const },
]

export default function Audit() {
  const { t } = useI18n()
  const { cases, can, notify } = useApp()
  const navigate = useNavigate()
  const [tab, setTab] = useState('audit')
  const [caseId, setCaseId] = useState('')
  const [action, setAction] = useState('')
  const [q, setQ] = useState('')
  const [busy, setBusy] = useState<string | null>(null)
  const [chain, setChain] = useState<any>(null)

  const auditQs = new URLSearchParams({ limit: '250' })
  if (caseId) auditQs.set('case_id', caseId)
  if (action) auditQs.set('action', action)

  const audit = useFetch<any>(`/api/audit?${auditQs.toString()}`, [caseId, action])
  const integrity = useFetch<any>('/api/integrity/overview', [])
  const ledger = useFetch<any>(can('ledger:read') ? '/api/ledger?limit=200' : null, [])
  const verifications = useFetch<any>('/api/verifications', [])

  const actions = useMemo(
    () => Array.from(new Set((audit.data?.records || []).map((r: any) => r.action))).sort() as string[],
    [audit.data],
  )
  const records = (audit.data?.records || []).filter((r: any) =>
    !q || JSON.stringify(r).toLowerCase().includes(q.toLowerCase()))
  const hasFilters = Boolean(caseId || action || q)

  async function verifyChain() {
    setBusy('chain')
    try {
      const res = await api.post<any>('/api/ledger/verify', {})
      setChain(res)
      notify(res.chain_intact ? 'success' : 'error',
        res.chain_intact ? 'Ledger chain intact' : 'Ledger chain broken',
        `${res.blocks} block(s) re-hashed at ${res.verified_at}.`)
      ledger.reload(); audit.reload()
    } catch (err) {
      notify('error', 'Verification failed', err instanceof ApiError ? err.message : undefined)
    } finally { setBusy(null) }
  }

  async function sweepIntegrity() {
    setBusy('sweep')
    try {
      const res = await api.post<any>('/api/integrity/run-all', {})
      notify(res.mismatches ? 'error' : 'success',
        res.mismatches ? `${res.mismatches} integrity mismatch detected` : 'All evidence objects verified',
        `${res.checked} object(s) re-hashed with SHA-256.`)
      integrity.reload(); audit.reload(); ledger.reload()
    } catch (err) {
      notify('error', 'Integrity sweep failed', err instanceof ApiError ? err.message : undefined)
    } finally { setBusy(null) }
  }

  function exportAudit() {
    const rows = records
    if (!rows.length) { notify('info', 'Nothing to export'); return }
    const cols = ['audit_id', 'timestamp', 'user_id', 'role', 'action', 'case_id', 'object_id', 'status', 'detail', 'hash']
    const csv = [
      '# CrimeNet AI audit export — SYNTHETIC DEMONSTRATION DATA',
      cols.join(','),
      ...rows.map((r: any) => cols.map((c) => `"${String(r[c] ?? '').replace(/"/g, '""')}"`).join(',')),
    ].join('\n')
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }))
    const a = document.createElement('a')
    a.href = url
    a.download = `crimenet-audit-${new Date().toISOString().slice(0, 10)}.csv`
    a.click()
    URL.revokeObjectURL(url)
    notify('success', 'Audit export generated', `${rows.length} record(s) exported as CSV.`)
  }

  const summary = integrity.data?.summary
  const chainState = chain || ledger.data?.verification

  return (
    <>
      <PageHeader
        tagline={t.pages.audit.tagline}
        title={t.pages.audit.title}
        description={t.pages.audit.description}
      >
        {can('evidence:integrity') && (
          <Button icon="shield" loading={busy === 'sweep'} onClick={sweepIntegrity}>Run integrity sweep</Button>
        )}
        {can('ledger:read') && (
          <Button variant="primary" icon="hash" loading={busy === 'chain'} onClick={verifyChain}>Verify ledger chain</Button>
        )}
      </PageHeader>

      <div className="mb-5 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Tile label="Audit records" value={audit.data?.total_records ?? '—'} hint="Append-only, SHA-256 per record" icon="audit" />
        <Tile label="Evidence verified" value={summary ? `${summary.verified}/${summary.total}` : '—'}
          hint={summary?.mismatch ? `${summary.mismatch} mismatch flagged` : 'No mismatch'} icon="shield" alert={Boolean(summary?.mismatch)} />
        <Tile label="Ledger blocks" value={chainState?.blocks ?? '—'}
          hint={ledger.data ? (chainState?.chain_intact ? 'Chain intact' : 'Chain broken') : 'Requires ledger:read'}
          icon="hash" alert={Boolean(ledger.data && chainState && !chainState.chain_intact)} />
        <Tile label="Human decisions" value={verifications.data?.count ?? '—'} hint="Verify / reject records" icon="check" />
      </div>

      <div className="mb-5 flex flex-wrap gap-1.5">
        {TABS.map((t_) => (
          <button
            key={t_.id}
            onClick={() => setTab(t_.id)}
            aria-pressed={tab === t_.id}
            className={`focus-ring flex items-center gap-1.5 rounded-[10px] px-3 py-2 text-[12.5px] font-semibold transition ${
              tab === t_.id
                ? 'bg-[var(--color-primary-deep)] text-white'
                : 'border border-[var(--color-border)] bg-[var(--color-surface-solid)] text-[var(--color-text)] hover:border-[var(--color-primary)]'
            }`}
          >
            <Icon name={t_.icon} size={14} />{t_.label}
          </button>
        ))}
      </div>

      {tab === 'audit' && (
        <Card solid title="Audit trail" icon="audit" subtitle={audit.data?.note}
          actions={can('audit:export') && <Button size="sm" icon="doc" onClick={exportAudit}>Export CSV</Button>}>
          <div className="mb-4 grid grid-cols-1 gap-2 md:grid-cols-3">
            <Select value={caseId} onChange={(e) => setCaseId(e.target.value)}>
              <option value="">All cases</option>
              {cases.map((c) => <option key={c.case_id} value={c.case_id}>{c.case_id}</option>)}
            </Select>
            <Select value={action} onChange={(e) => setAction(e.target.value)}>
              <option value="">All actions</option>
              {actions.map((a) => <option key={a} value={a}>{a}</option>)}
            </Select>
            <TextInput placeholder="Search user, object, detail…" value={q} onChange={(e) => setQ(e.target.value)} />
          </div>
          {audit.loading && <LoadingBlock label="Loading audit records…" variant="table" />}
          {audit.error && <ErrorState message={audit.error} onRetry={audit.reload} />}
          {audit.data && records.length === 0 && (
            <EmptyState title="No audit record matches these filters" icon="search"
              message="Records are append-only: clearing the filters restores the full trail."
              action={hasFilters
                ? <Button size="sm" icon="reset" onClick={() => { setCaseId(''); setAction(''); setQ('') }}>Clear filters</Button>
                : undefined} />
          )}
          {audit.data && records.length > 0 && (
            <div className="max-h-[620px] overflow-auto rounded-[10px] border border-[var(--color-border)]">
              <table className="w-full min-w-[980px] text-left text-[12px]">
                <thead className="sticky top-0">
                  <tr>
                    {['ID', 'Timestamp', 'Actor', 'Action', 'Object', 'Status', 'Detail', 'Record hash'].map((h) => (
                      <th key={h} className="border-b border-[var(--color-border)] bg-[var(--color-primary-soft)] px-2.5 py-2 text-[10.5px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="bg-[var(--color-surface-solid)]">
                  {records.map((r: any) => (
                    <tr key={r.audit_id} className="border-b border-[var(--color-border)] last:border-0 hover:bg-[var(--color-primary-soft)]/50">
                      <td className="mono-id whitespace-nowrap px-2.5 py-1.5 text-[var(--color-text-muted)]">{r.audit_id}</td>
                      <td className="mono-id whitespace-nowrap px-2.5 py-1.5 text-[var(--color-text)]">{r.timestamp.replace('T', ' ').replace('Z', '')}</td>
                      <td className="px-2.5 py-1.5 text-[var(--color-text)]">
                        <span className="mono-id">{r.user_id}</span>
                        <span className="block text-[10.5px] text-[var(--color-text-muted)]">{r.role}</span>
                      </td>
                      <td className="px-2.5 py-1.5 font-semibold text-[var(--color-primary-deep)]">{r.action}</td>
                      <td className="mono-id px-2.5 py-1.5 text-[var(--color-text)]">{r.object_id || r.case_id || '—'}</td>
                      <td className="px-2.5 py-1.5"><StatusPill status={r.status} /></td>
                      <td className="max-w-[300px] truncate px-2.5 py-1.5 text-[var(--color-text-muted)]" title={r.detail}>{r.detail}</td>
                      <td className="px-2.5 py-1.5"><Hash value={r.hash} chars={10} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}

      {tab === 'integrity' && (
        <Card solid title="Evidence integrity register" icon="shield"
          subtitle={integrity.data ? `${integrity.data.algorithm} · ${integrity.data.policy}` : ''}>
          {integrity.loading && <LoadingBlock label="Loading integrity register…" variant="table" />}
          {integrity.error && <ErrorState message={integrity.error} onRetry={integrity.reload} />}
          {integrity.data && integrity.data.items.length === 0 && (
            <EmptyState title="No evidence objects registered yet" icon="evidence" />
          )}
          {integrity.data && integrity.data.items.length > 0 && (
            <div className="-mx-5 overflow-x-auto">
              <table className="w-full min-w-[920px] text-left text-[12.5px]">
                <thead>
                  <tr>
                    {['Evidence', 'Case', 'Type', 'SHA-256', 'Integrity', 'Human review', 'Last checked', ''].map((h, i) => (
                      <th key={h + i} className="border-b border-[var(--color-border)] bg-[var(--color-primary-soft)] px-2.5 py-2 text-[10.5px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {integrity.data.items.map((i: any) => {
                    const bad = i.integrity_status !== 'VERIFIED'
                    return (
                      <tr key={i.evidence_id}
                        className={`border-b border-[var(--color-border)] last:border-0 ${bad ? 'bg-[rgba(196,52,31,0.06)]' : 'hover:bg-[var(--color-primary-soft)]/50'}`}>
                        <td className="mono-id px-2.5 py-1.5 font-semibold text-[var(--color-primary-deep)]">{i.evidence_id}</td>
                        <td className="mono-id px-2.5 py-1.5">{i.case_id}</td>
                        <td className="px-2.5 py-1.5 text-[var(--color-text-muted)]">{i.type}</td>
                        <td className="px-2.5 py-1.5"><Hash value={i.sha256} chars={12} /></td>
                        <td className="px-2.5 py-1.5"><StatusPill status={i.integrity_status} /></td>
                        <td className="px-2.5 py-1.5"><StatusPill status={i.verification_status} /></td>
                        <td className="mono-id whitespace-nowrap px-2.5 py-1.5 text-[11.5px] text-[var(--color-text-muted)]">
                          {i.last_checked ? i.last_checked.replace('T', ' ').replace('Z', '') : 'never'}
                        </td>
                        <td className="px-2.5 py-1.5">
                          <Button size="sm" icon="eye" onClick={() => navigate(`/evidence?focus=${i.evidence_id}`)}>Open</Button>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
          {summary?.mismatch > 0 && (
            <p className="mt-3 flex items-start gap-2 rounded-[10px] border border-[var(--color-danger)] bg-[rgba(196,52,31,0.06)] px-3 py-2 text-[12.5px] text-[var(--color-text)]">
              <Icon name="alert" size={13} className="mt-0.5 text-[var(--color-danger)]" />
              <span>
                A hash mismatch means the stored object no longer matches the hash registered at intake. The
                registered hash is preserved and the object is flagged as suspect — the original evidence is never
                modified or deleted by the platform.
              </span>
            </p>
          )}
        </Card>
      )}

      {tab === 'ledger' && (
        <Card solid title="Permissioned ledger (evidence notarisation)" icon="hash" subtitle={ledger.data?.profile}>
          {!can('ledger:read') && (
            <p className="text-[13px] text-[var(--color-text)]">
              Your role does not hold the <span className="mono-id">ledger:read</span> permission.
            </p>
          )}
          {ledger.loading && <LoadingBlock label="Loading ledger blocks…" variant="table" />}
          {ledger.error && <ErrorState message={ledger.error} onRetry={ledger.reload} />}
          {ledger.data && (
            <>
              <div className="mb-4 grid grid-cols-1 gap-2 md:grid-cols-3">
                <div className="rounded-[10px] border border-[var(--color-border)] px-3 py-2">
                  <p className="text-[10.5px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">Chain state</p>
                  <p className="mt-0.5 text-[13px] font-semibold text-[var(--color-primary-deep)]">
                    {chainState?.chain_intact ? 'INTACT' : 'BROKEN'} · <span className="data-num">{chainState?.blocks}</span> blocks
                  </p>
                </div>
                <div className="rounded-[10px] border border-[var(--color-border)] px-3 py-2">
                  <p className="text-[10.5px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">Head hash</p>
                  <p className="mt-1"><Hash value={chainState?.head_hash} chars={20} /></p>
                </div>
                <div className="rounded-[10px] border border-[var(--color-border)] px-3 py-2">
                  <p className="text-[10.5px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">Authority set</p>
                  <p className="mono-id mt-0.5 text-[11.5px] font-semibold text-[var(--color-text)]">{ledger.data.authority_set.join(', ')}</p>
                </div>
              </div>
              {/* honesty banner: this is an abstraction, not a production chain */}
              <p className="banner-honesty mb-3 flex items-start gap-2 px-3 py-2 text-[12px]">
                <Icon name="info" size={13} />
                <span>
                  This is a clearly labelled permissioned-ledger abstraction used for evidence notarisation in this
                  deployment profile. No production blockchain network is running. Stored per block:{' '}
                  <span className="mono-id">{ledger.data.stored_fields.join(', ')}</span>. Never stored:{' '}
                  <span className="mono-id">{ledger.data.never_stored.join(', ')}</span>.
                </span>
              </p>
              <div className="max-h-[520px] space-y-2 overflow-y-auto pr-1">
                {ledger.data.blocks.map((b: any) => (
                  <div key={b.index} className="rounded-[10px] border border-[var(--color-border)] px-3.5 py-2.5">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <p className="text-[12.5px] font-semibold text-[var(--color-primary-deep)]">
                        Block <span className="data-num">#{b.index}</span> · {b.event_type}
                      </p>
                      <div className="flex items-center gap-1.5">
                        <span className="mono-id rounded bg-[var(--color-primary-soft)] px-1.5 py-0.5 text-[11px] text-[var(--color-primary-deep)]">{b.evidence_id || '—'}</span>
                        <StatusPill status={b.integrity_status} />
                      </div>
                    </div>
                    <p className="mono-id mt-1 text-[11px] text-[var(--color-text-muted)]">
                      {b.timestamp.replace('T', ' ').replace('Z', '')} · {b.case_id || 'no case'} · notary {b.recorded_by}
                    </p>
                    <div className="mt-2 grid grid-cols-1 gap-1.5 sm:grid-cols-3">
                      <LedgerHash label="payload" value={b.payload_hash} />
                      <LedgerHash label="previous" value={b.previous_hash} />
                      <LedgerHash label="block" value={b.block_hash} />
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </Card>
      )}

      {tab === 'verifications' && (
        <Card solid title="Human verification decisions" icon="check"
          subtitle="Analytical findings are advisory until a human decides. Rejected findings are retained, never deleted.">
          {verifications.loading && <LoadingBlock label="Loading decisions…" variant="table" />}
          {verifications.error && <ErrorState message={verifications.error} onRetry={verifications.reload} />}
          {(verifications.data?.verifications || []).length === 0 && !verifications.loading && (
            <EmptyState title="No human decision recorded yet" icon="check"
              message="Every verify / reject decision taken anywhere in the console appears here with its rationale." />
          )}
          <div className="space-y-2">
            {(verifications.data?.verifications || []).map((v: any) => (
              <div key={v.record_id} className="rounded-[10px] border border-[var(--color-border)] px-3.5 py-2.5">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="text-[12.5px] font-semibold text-[var(--color-primary-deep)]">
                    <span className="mono-id">{v.record_id}</span> · {v.object_type} <span className="mono-id">{v.object_id}</span>
                  </p>
                  <StatusPill status={v.decision} />
                </div>
                <p className="mono-id mt-1 text-[11px] text-[var(--color-text-muted)]">
                  {v.verified_by} ({v.role}) · {v.timestamp.replace('T', ' ').replace('Z', '')} · {v.case_id || 'no case'}
                </p>
                {v.rationale && <p className="mt-1.5 text-[12.5px] text-[var(--color-text)]">{v.rationale}</p>}
                {v.evidence_ids?.length > 0 && (
                  <div className="mt-1.5">
                    <SectionHeader>Cited evidence</SectionHeader>
                    <p className="mono-id text-[11px] text-[var(--color-text-muted)]">{v.evidence_ids.join(' · ')}</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </Card>
      )}
    </>
  )
}

function Tile({ label, value, hint, icon, alert = false }: {
  label: string; value: React.ReactNode; hint?: string; icon: any; alert?: boolean
}) {
  return (
    <div className="surface-solid px-4 py-3.5">
      <div className="flex items-start justify-between gap-2">
        <p className="section-header !text-[12px]">{label}</p>
        <span className={`rounded-lg border px-1.5 py-1 ${
          alert ? 'border-[var(--color-warning)] text-[var(--color-warning)]' : 'border-[var(--color-border)] text-[var(--color-text-muted)]'
        }`}>
          <Icon name={icon} size={14} />
        </span>
      </div>
      <p className="data-num mt-2 text-[22px] font-semibold leading-none text-[var(--color-primary-deep)]">{value}</p>
      {hint && <p className="mt-1.5 text-[12px] leading-snug text-[var(--color-text-muted)]">{hint}</p>}
    </div>
  )
}

function LedgerHash({ label, value }: { label: string; value?: string }) {
  return (
    <div className="rounded-md border border-[var(--color-border)] px-2 py-1">
      <p className="text-[10px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">{label}</p>
      <Hash value={value} chars={14} />
    </div>
  )
}
