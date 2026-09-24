import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApp } from '../state/AppContext'
import { api, ApiError } from '../services/api'
import {
  Badge, Button, Card, EmptyState, ErrorState, Field, LoadingBlock, Modal, PageHeader, Select,
  StatusBadge, TextArea, TextInput,
} from '../components/shared/ui'
import { Icon } from '../components/shared/Icon'
import type { CaseOut } from '../types'
import { useI18n } from '../i18n/LanguageContext'

const PRIORITY_TONE: Record<string, any> = { CRITICAL: 'red', HIGH: 'amber', MEDIUM: 'blue', LOW: 'slate' }

export default function Cases() {
  const { t, tok } = useI18n()
  const { cases, casesLoading, casesError, refreshCases, can, notify, setActiveCase } = useApp()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [filter, setFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [form, setForm] = useState({
    case_id: '', title: '', case_type: 'Vehicle Theft', priority: 'MEDIUM',
    description: '', status: 'OPEN',
  })

  const visible = cases.filter((c) =>
    (!filter || `${c.case_id} ${c.title} ${c.case_type}`.toLowerCase().includes(filter.toLowerCase())) &&
    (!statusFilter || c.status === statusFilter))

  async function create(e: React.FormEvent) {
    e.preventDefault()
    setErr(null)
    if (form.title.trim().length < 3) { setErr('Case title must be at least 3 characters.'); return }
    if (form.case_id && !/^CASE-\d{3,4}$/.test(form.case_id)) { setErr('Case ID must look like CASE-101 (or leave blank to auto-generate).'); return }
    setBusy(true)
    try {
      const created = await api.post<CaseOut>('/api/cases', {
        ...form, case_id: form.case_id || undefined,
      })
      notify('success', t.cases.caseCreated(created.case_id), created.title)
      setOpen(false)
      setForm({ case_id: '', title: '', case_type: 'Vehicle Theft', priority: 'MEDIUM', description: '', status: 'OPEN' })
      await refreshCases()
      navigate(`/cases/${created.case_id}`)
    } catch (error) {
      setErr(error instanceof ApiError ? error.message : t.cases.createFailed)
    } finally { setBusy(false) }
  }

  return (
    <>
      <PageHeader
        tagline={t.pages.cases.tagline}
        title={t.pages.cases.title}
        description={t.pages.cases.description}
      >
        <Button icon="refresh" onClick={refreshCases}>{t.cases.refresh}</Button>
        {can('case:create') && <Button variant="primary" icon="plus" onClick={() => setOpen(true)}>{t.cases.createCase}</Button>}
      </PageHeader>

      <Card solid
        title={t.cases.authorizedCases(visible.length)} icon="cases"
        subtitle={t.cases.allSynthetic}
        actions={
          <>
            <TextInput placeholder={t.cases.filterCases} value={filter} onChange={(e) => setFilter(e.target.value)} className="w-40 sm:w-56" />
            <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="w-32">
              <option value="">{t.cases.allStatus}</option>
              <option value="OPEN">{t.tokens.caseStatus.OPEN}</option>
              <option value="ACTIVE">{t.tokens.caseStatus.ACTIVE}</option>
              <option value="UNDER_REVIEW">{t.tokens.caseStatus.UNDER_REVIEW}</option>
              <option value="CLOSED">{t.tokens.caseStatus.CLOSED}</option>
            </Select>
          </>
        }
      >
        {casesLoading && <LoadingBlock label={t.cases.loadingCases} />}
        {!casesLoading && casesError && <ErrorState message={casesError} onRetry={() => refreshCases()} />}
        {!casesLoading && !casesError && visible.length === 0 && (
          <EmptyState title={t.cases.noCasesTitle} message={t.cases.noCasesBody} icon="cases" />
        )}
        <div className="stagger grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
          {visible.map((c) => (
            <article key={c.case_id} className="surface-solid lift group flex flex-col px-4 py-3.5">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="text-[12px] font-bold tracking-wide text-[var(--color-primary)]">{c.case_id}</p>
                  <h3 className="mt-0.5 text-[15px] font-bold leading-snug text-[var(--color-primary-deep)]">{c.title}</h3>
                </div>
                <Badge tone={PRIORITY_TONE[c.priority]}>{tok(t.tokens.priority, c.priority)}</Badge>
              </div>
              <p className="mt-1.5 line-clamp-3 text-[12.5px] leading-relaxed text-[var(--color-text-muted)]/85">{c.description}</p>
              <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
                <StatusBadge status={c.status} />
                <Badge tone="slate">{t.cases.caseTypes[c.case_type] || c.case_type}</Badge>
                <Badge tone="navy">{c.investigator}</Badge>
              </div>
              <dl className="mt-3 grid grid-cols-3 gap-2 rounded-lg bg-[var(--color-surface-solid)] px-2.5 py-2 text-center ring-1 ring-[rgba(147,194,251,0.4)]">
                {[[t.cases.colEvidence, c.evidence_count], [t.cases.colEntities, c.entity_count], [t.cases.colLinks, c.relationship_count]].map(([k, v]) => (
                  <div key={k as string}>
                    <dt className="text-[10px] font-bold uppercase tracking-wide text-[var(--color-text-muted)]/60">{k}</dt>
                    <dd className="text-[16px] font-bold text-[var(--color-primary-deep)]">{v as number}</dd>
                  </div>
                ))}
              </dl>
              <div className="mt-3 flex gap-2">
                <Button size="sm" variant="primary" icon="arrowRight" className="flex-1" onClick={() => navigate(`/cases/${c.case_id}`)}>{t.cases.openCase}</Button>
                <Button size="sm" icon="target" onClick={() => { setActiveCase(c.case_id); notify('info', t.cases.contextSetTo(c.case_id)) }}>{t.cases.setContext}</Button>
              </div>
              <p className="mt-2 text-[10.5px] uppercase tracking-wider text-amber-700">{c.classification}</p>
            </article>
          ))}
        </div>
      </Card>

      <Modal
        open={open} onClose={() => setOpen(false)} title={t.cases.createTitle}
        subtitle={t.cases.createSubtitle}
        footer={
          <>
            <Button size="sm" onClick={() => setOpen(false)}>{t.cases.cancel}</Button>
            <Button size="sm" variant="primary" icon="plus" loading={busy} onClick={create as any}>{t.cases.createCase}</Button>
          </>
        }
      >
        <form onSubmit={create} className="space-y-3">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <Field label={t.cases.fieldCaseId} hint={t.cases.fieldCaseIdHint}>
              <TextInput value={form.case_id} onChange={(e) => setForm({ ...form, case_id: e.target.value.toUpperCase() })} placeholder="CASE-601" />
            </Field>
            <Field label={t.cases.fieldTitle} required>
              <TextInput value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} placeholder={t.cases.fieldTitlePlaceholder} />
            </Field>
            <Field label={t.cases.fieldType} required>
              <Select value={form.case_type} onChange={(e) => setForm({ ...form, case_type: e.target.value })}>
                {['Vehicle Theft', 'Property Crime', 'Financial', 'Document Fraud', 'Preliminary Inquiry', 'Organised Property Crime'].map((ct) => (
                  <option key={ct} value={ct}>{t.cases.caseTypes[ct] || ct}</option>
                ))}
              </Select>
            </Field>
            <Field label={t.cases.fieldPriority}>
              <Select value={form.priority} onChange={(e) => setForm({ ...form, priority: e.target.value })}>
                {['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'].map((p) => <option key={p} value={p}>{tok(t.tokens.priority, p)}</option>)}
              </Select>
            </Field>
            <Field label={t.cases.fieldStatus}>
              <Select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
                {['OPEN', 'ACTIVE', 'UNDER_REVIEW', 'CLOSED'].map((cs) => <option key={cs} value={cs}>{tok(t.tokens.caseStatus, cs)}</option>)}
              </Select>
            </Field>
          </div>
          <Field label={t.cases.fieldDescription}>
            <TextArea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })}
              placeholder={t.cases.fieldDescriptionPlaceholder} />
          </Field>
          {err && (
            <p className="flex items-start gap-2 rounded-lg border border-[var(--color-danger)] bg-[rgba(196,52,31,0.06)] px-3 py-2 text-[12.5px] text-[var(--color-danger)]">
              <Icon name="alert" size={15} /> {err}
            </p>
          )}
        </form>
      </Modal>
    </>
  )
}
