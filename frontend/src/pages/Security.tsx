import { useState } from 'react'
import { useApp } from '../state/AppContext'
import { useFetch } from '../hooks/useFetch'
import { api, ApiError } from '../services/api'
import { Icon } from '../components/shared/Icon'
import {
  Badge, Button, Card, EmptyState, ErrorState, Field, Hash, LoadingBlock, Modal, PageHeader,
  SectionHeader, Select, StatusPill, TextInput,
} from '../components/shared/ui'
import { useI18n } from '../i18n/LanguageContext'

/* ============================================================================
   SECURITY & ASSURANCE
   The most serious surface in the product. Deliberately austere: near-monochrome
   (primary-deep text on solid white, muted borders), colour reserved for state
   that matters — a mismatch, a prohibition, a granted permission. Every table is
   dense and sits on a solid surface; glass is used only on the small summary
   tiles at the top, never behind the RBAC matrix or the user table.
   ============================================================================ */

const TABS = [
  { id: 'posture', label: 'Security posture', icon: 'shield' as const },
  { id: 'rbac', label: 'Roles & permissions', icon: 'lock' as const },
  { id: 'agents', label: 'Agents & least privilege', icon: 'spark' as const },
  { id: 'backends', label: 'Data & AI backends', icon: 'security' as const },
  { id: 'aisafety', label: 'AI safety posture', icon: 'info' as const },
  { id: 'users', label: 'User management', icon: 'user' as const },
]

export default function Security() {
  const { t } = useI18n()
  const { user, can, notify, cases } = useApp()
  const [tab, setTab] = useState('posture')

  const status = useFetch<any>(can('security:read') ? '/api/security/status' : null, [])
  const rbac = useFetch<any>(can('security:read') ? '/api/security/rbac' : null, [])
  const agents = useFetch<any>('/api/security/agents', [])
  const safety = useFetch<any>(can('security:read') ? '/api/security/ai-safety-posture' : null, [])
  const users = useFetch<any>(can('user:manage') ? '/api/security/users' : null, [])

  const s = status.data

  return (
    <>
      <PageHeader
        tagline={t.pages.security.tagline}
        title={t.pages.security.title}
        description={t.pages.security.description}
      >
        <Button icon="refresh" onClick={() => { status.reload(); rbac.reload(); agents.reload(); safety.reload(); users.reload() }}>
          Refresh
        </Button>
      </PageHeader>

      {/* summary tiles — glass is fine here: four numbers, one line each */}
      <div className="stagger mb-5 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Tile label="Signed in as" value={user?.user_id || '—'} hint={`${user?.display_name || ''} · ${user?.role || ''}`} icon="user" />
        <Tile label="Session" value={s ? `${s.authentication.session_lifetime_minutes} min` : '—'}
          hint={s ? `${s.authentication.mechanism} · ${s.authentication.algorithm}` : ''} icon="lock" />
        <Tile label="Case access" value={s ? (s.authorization.case_access[0] === '*' ? 'ALL' : s.authorization.case_access.length) : '—'}
          hint={s ? s.authorization.model : ''} icon="cases" />
        <Tile label="Evidence integrity" value={s ? `${s.evidence_integrity.verified}/${s.evidence_integrity.total}` : '—'}
          hint={s?.evidence_integrity.mismatch ? `${s.evidence_integrity.mismatch} mismatch flagged` : 'All objects match their intake hash'}
          icon="shield" alert={Boolean(s?.evidence_integrity.mismatch)} />
      </div>

      <div className="mb-5 flex flex-wrap gap-1.5">
        {TABS.filter((tab_) => tab_.id !== 'users' || can('user:manage')).map((tab_) => (
          <button
            key={tab_.id}
            onClick={() => setTab(tab_.id)}
            aria-pressed={tab === tab_.id}
            className={`focus-ring flex items-center gap-1.5 rounded-[10px] px-3 py-2 text-[12.5px] font-semibold transition ${
              tab === tab_.id
                ? 'bg-[var(--color-primary-deep)] text-white'
                : 'border border-[var(--color-border)] bg-[var(--color-surface-solid)] text-[var(--color-text)] hover:border-[var(--color-primary)]'
            }`}
          >
            <Icon name={tab_.icon} size={14} />{tab_.label}
          </button>
        ))}
      </div>

      {!can('security:read') && tab !== 'agents' && (
        <Card solid title="Restricted" icon="lock">
          <p className="text-[13px] text-[var(--color-text)]">
            Your role does not hold the <span className="mono-id">security:read</span> permission. The security
            posture surface is restricted server-side.
          </p>
        </Card>
      )}

      {status.loading && <LoadingBlock label="Reading security posture…" rows={3} variant="table" />}
      {status.error && <ErrorState message={status.error} onRetry={status.reload} />}

      {tab === 'posture' && s && (
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
          <Card solid title="Authentication" icon="lock">
            <KV items={[
              ['Status', <StatusPill key="a" status={s.authentication.status} />],
              ['Mechanism', s.authentication.mechanism],
              ['Algorithm', s.authentication.algorithm],
              ['Session lifetime', `${s.authentication.session_lifetime_minutes} minutes`],
              ['Principal', `${s.authentication.user} — ${s.authentication.display_name}`],
              ['Role', s.authentication.role],
            ]} />
          </Card>

          <Card solid title="Authorization" icon="shield" subtitle={s.authorization.enforcement}>
            <p className="text-[12.5px] text-[var(--color-text)]">{s.authorization.role_summary}</p>
            <SectionHeader>Granted permissions</SectionHeader>
            <div className="flex flex-wrap gap-1.5">
              {s.authorization.permissions.map((p: string) => (
                <span key={p} className="mono-id rounded border border-[var(--color-border)] bg-[var(--color-primary-soft)] px-1.5 py-0.5 font-semibold text-[var(--color-primary-deep)]">
                  {p}
                </span>
              ))}
            </div>
            <SectionHeader>Case scope</SectionHeader>
            <p className="mono-id text-[12.5px] font-semibold text-[var(--color-text)]">{s.authorization.case_access.join(', ')}</p>
          </Card>

          <Card solid title="Transport & encryption" icon="security">
            <KV items={[
              ['TLS', s.transport.tls],
              ['Transport detail', s.transport.detail],
              ['Field encryption', s.encryption.at_rest_fields],
              ['Password storage', s.encryption.password_storage],
              ['Evidence hashing', s.encryption.evidence_hashing],
            ]} />
            <p className="mt-3 flex items-start gap-2 rounded-[10px] border border-[var(--color-warning)] bg-[rgba(184,121,26,0.06)] px-3 py-2 text-[11.5px] text-[var(--color-text)]">
              <Icon name="info" size={12} /> <span>{s.encryption.production_note}</span>
            </p>
          </Card>

          <Card solid title="Audit & ledger" icon="hash">
            <KV items={[
              ['Audit records', `${s.audit.records} (append-only: ${String(s.audit.append_only)})`],
              ['Per-record hash', s.audit.per_record_hash],
              ['Ledger profile', s.ledger.profile],
              ['Blocks', `${s.ledger.blocks} · chain intact: ${String(s.ledger.chain_intact)}`],
              ['Head hash', <Hash key="h" value={s.ledger.head_hash} chars={22} />],
            ]} />
          </Card>

          <Card solid title="Agent prohibitions" icon="reject" className="lg:col-span-2">
            <ul className="grid grid-cols-1 gap-2 md:grid-cols-2">
              {s.agent_prohibitions.map((p: string, i: number) => (
                <li key={i} className="flex items-start gap-2 rounded-[10px] border border-[var(--color-border)] px-3 py-2 text-[12.5px] text-[var(--color-text)]">
                  <span className="mt-0.5 text-[var(--color-danger)]"><Icon name="reject" size={13} /></span>{p}
                </li>
              ))}
            </ul>
            <p className="mt-3 text-[12px] text-[var(--color-text)]">
              <span className="font-semibold">Least privilege:</span> {s.least_privilege}
            </p>
            <p className="mono-id mt-1 text-[11px] text-[var(--color-text-muted)]">
              Classification: {s.classification} · platform v{s.version} · checked {s.checked_at.replace('T', ' ').replace('Z', '')}
            </p>
          </Card>
        </div>
      )}

      {tab === 'rbac' && rbac.data && (
        <Card solid title="Role-based access control matrix" icon="lock"
          subtitle="Enforced by a FastAPI dependency guard on every endpoint — the frontend never grants access.">
          <div className="-mx-5 overflow-x-auto">
            <table className="w-full min-w-[720px] text-left text-[12.5px]">
              <thead>
                <tr>
                  {['Permission', 'Description', 'INVESTIGATOR', 'ANALYST', 'SUPERVISOR', 'ADMIN'].map((h, i) => (
                    <th key={h} className={`border-b border-[var(--color-border)] bg-[var(--color-primary-soft)] px-2.5 py-2 text-[10.5px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)] ${i > 1 ? 'text-center' : ''}`}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rbac.data.matrix.map((row: any) => (
                  <tr key={row.permission} className="border-b border-[var(--color-border)] last:border-0 hover:bg-[var(--color-primary-soft)]/50">
                    <td className="mono-id px-2.5 py-1.5 font-semibold text-[var(--color-primary-deep)]">{row.permission}</td>
                    <td className="px-2.5 py-1.5 text-[var(--color-text-muted)]">{row.description}</td>
                    {['INVESTIGATOR', 'ANALYST', 'SUPERVISOR', 'ADMIN'].map((r) => (
                      <td key={r} className="px-2.5 py-1.5 text-center">
                        {row.roles.includes(r)
                          ? <span className="text-[var(--color-success)]"><Icon name="check" size={15} /></span>
                          : <span className="text-[var(--color-text-muted)]/40"><Icon name="close" size={14} /></span>}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-4 grid grid-cols-1 gap-2 md:grid-cols-2">
            {Object.entries(rbac.data.roles).map(([role, def]: any) => (
              <div key={role} className="rounded-[10px] border border-[var(--color-border)] px-3.5 py-2.5">
                <p className="flex items-center gap-2 text-[12.5px] font-semibold text-[var(--color-primary-deep)]">
                  {role}
                  <span className="data-num rounded bg-[var(--color-primary-soft)] px-1.5 text-[11px] font-semibold text-[var(--color-primary-deep)]">
                    {def.permissions.length} permissions
                  </span>
                </p>
                <p className="mt-0.5 text-[12px] text-[var(--color-text-muted)]">{def.summary}</p>
              </div>
            ))}
          </div>
        </Card>
      )}

      {tab === 'agents' && (
        <Card solid title="Agent registry" icon="spark" subtitle={agents.data?.note}>
          {agents.loading && <LoadingBlock label="Loading agent registry…" />}
          {agents.error && <ErrorState message={agents.error} onRetry={agents.reload} />}
          <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
            {(agents.data?.agents || []).map((a: any) => {
              const reg = (agents.data?.registry || []).find((r: any) => r.agent === a.name)
              return (
                <div key={a.name} className="rounded-[10px] border border-[var(--color-border)] px-3.5 py-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="text-[13px] font-semibold text-[var(--color-primary-deep)]">{a.name.replace(/_/g, ' ')}</p>
                    <Badge tone="slate">{a.kind}</Badge>
                  </div>
                  <ul className="mt-2 space-y-1">
                    {a.responsibilities.map((r: string, i: number) => (
                      <li key={i} className="flex items-start gap-1.5 text-[12px] text-[var(--color-text)]">
                        <span className="mt-0.5 text-[var(--color-primary)]"><Icon name="check" size={12} /></span>{r}
                      </li>
                    ))}
                  </ul>
                  {reg && (
                    <div className="mt-2.5 grid grid-cols-1 gap-2 sm:grid-cols-2">
                      <div>
                        <p className="text-[10.5px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">Permitted</p>
                        <div className="mt-1 flex flex-wrap gap-1">
                          {reg.permissions.map((p: string) => (
                            <span key={p} className="mono-id rounded border border-[var(--color-border)] bg-[var(--color-primary-soft)] px-1.5 py-0.5 text-[10.5px] text-[var(--color-primary-deep)]">{p}</span>
                          ))}
                        </div>
                      </div>
                      <div>
                        <p className="text-[10.5px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">Forbidden</p>
                        <div className="mt-1 flex flex-wrap gap-1">
                          {reg.forbidden.map((p: string) => (
                            <span key={p} className="rounded border border-dashed border-[var(--color-danger)] px-1.5 py-0.5 text-[10.5px] text-[var(--color-danger)]">{p}</span>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}
                  <p className="mono-id mt-2 text-[11px] text-[var(--color-text-muted)]">{a.implementation}</p>
                </div>
              )
            })}
          </div>
        </Card>
      )}

      {tab === 'backends' && s && (
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
          {Object.entries(s.data_backends).map(([key, b]: any) => (
            <Card key={key} solid title={b.component} icon="security" subtitle={b.profile}
              actions={
                <Badge tone={b.profile?.includes('EMBEDDED') || b.profile?.includes('FILESYSTEM') ? 'amber' : 'green'}
                       dashed={b.profile?.includes('EMBEDDED') || b.profile?.includes('FILESYSTEM')}>
                  {b.profile?.includes('EMBEDDED') || b.profile?.includes('FILESYSTEM') ? 'DEV PROFILE' : 'CONNECTED'}
                </Badge>
              }>
              <p className="text-[12.5px] text-[var(--color-text)]">{b.detail}</p>
              <div className="mt-2.5 flex flex-wrap gap-1.5">
                {Object.entries(b).filter(([k]) => !['component', 'profile', 'detail', 'tables'].includes(k)).map(([k, v]: any) => (
                  <span key={k} className="rounded border border-[var(--color-border)] px-2 py-1 text-[11px] font-medium text-[var(--color-text)]">
                    {k.replace(/_/g, ' ')}: <span className="data-num font-semibold">{String(v)}</span>
                  </span>
                ))}
              </div>
              {b.tables && (
                <div className="mt-2.5 grid grid-cols-2 gap-1.5 sm:grid-cols-3">
                  {Object.entries(b.tables).map(([tb, n]: any) => (
                    <span key={tb} className="rounded border border-[var(--color-border)] px-2 py-1 text-[11px] text-[var(--color-text)]">
                      {tb}: <span className="data-num font-semibold">{n}</span>
                    </span>
                  ))}
                </div>
              )}
            </Card>
          ))}
          <Card solid title="NER / document intelligence" icon="doc">
            <KV items={[
              ['NER backend', s.ai_backends.ner.ner_backend],
              ['Transformers', s.ai_backends.ner.transformers_backend],
              ['Rule layer', s.ai_backends.ner.rule_layer],
            ]} />
          </Card>
          <Card solid title="OCR" icon="doc">
            <KV items={[
              ['Available', String(s.ai_backends.ocr.available)],
              ['Backend', s.ai_backends.ocr.backend],
              ['Detail', s.ai_backends.ocr.detail],
            ]} />
            <p className="mt-3 flex items-start gap-2 rounded-[10px] border border-[var(--color-warning)] bg-[rgba(184,121,26,0.06)] px-3 py-2 text-[11.5px] text-[var(--color-text)]">
              <Icon name="info" size={12} />
              <span>The platform never claims OCR ran when it did not. Image and PDF evidence is registered,
                hashed and marked as awaiting an OCR-capable deployment.</span>
            </p>
          </Card>
        </div>
      )}

      {tab === 'aisafety' && (
        <div className="space-y-5">
          {safety.loading && <LoadingBlock label="Reading AI safety posture…" rows={3} variant="table" />}
          {safety.error && <ErrorState message={safety.error} onRetry={safety.reload} />}
          {safety.data && (
            <>
              <Card solid title="Is a generative model in the evidence path?" icon="shield"
                subtitle="The question a supervisor should be able to answer without reading the source.">
                <p className={`inline-flex items-center gap-2 rounded-[10px] px-3 py-2 text-[13px] font-semibold ${
                  safety.data.generative_model_in_evidence_path ? 'status-rejected' : 'status-verified'
                }`}>
                  <Icon name={safety.data.generative_model_in_evidence_path ? 'alert' : 'check'} size={15} />
                  generative_model_in_evidence_path: {String(safety.data.generative_model_in_evidence_path)}
                </p>
                <p className="mt-3 text-[12.5px] leading-relaxed text-[var(--color-text)]">{safety.data.reasoning}</p>
                <p className="mono-id mt-3 rounded-[10px] border border-[var(--color-border)] bg-[var(--color-primary-soft)] px-3 py-2 text-[11.5px] text-[var(--color-primary-deep)]">
                  verified_by {safety.data.verified_by} · checked_by {safety.data.checked_by} · checked_at {safety.data.checked_at}
                </p>
              </Card>

              <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
                <Card solid title="What that means in practice" icon="info">
                  <ul className="space-y-2">
                    {Object.entries(safety.data.what_that_means).map(([k, v]: any) => (
                      <li key={k} className="rounded-[10px] border border-[var(--color-border)] px-3 py-2">
                        <p className="mono-id text-[11.5px] font-semibold text-[var(--color-primary-deep)]">{k}: {String(v)}</p>
                      </li>
                    ))}
                  </ul>
                </Card>

                <Card solid title="Model inventory" icon="spark">
                  <ul className="divide-y divide-[var(--color-border)]">
                    {Object.entries(safety.data.model_inventory).map(([k, v]: any) => (
                      <li key={k} className="py-2 first:pt-0">
                        <p className="text-[12px] font-semibold uppercase tracking-wide text-[var(--color-text-muted)]">{k}</p>
                        <p className="mt-0.5 text-[12.5px] text-[var(--color-text)]">{String(v)}</p>
                      </li>
                    ))}
                  </ul>
                </Card>
              </div>

              <Card solid title="Residual risks we do not claim to have solved" icon="alert">
                <ul className="space-y-2">
                  {(safety.data.residual_risks_we_do_not_claim_to_have_solved || []).map((r: string, i: number) => (
                    <li key={i} className="flex items-start gap-2 rounded-[10px] border border-[var(--color-warning)] bg-[rgba(184,121,26,0.05)] px-3 py-2 text-[12.5px] text-[var(--color-text)]">
                      <span className="mt-0.5 text-[var(--color-warning)]"><Icon name="info" size={13} /></span>{r}
                    </li>
                  ))}
                </ul>
                <p className="mono-id mt-3 text-[11px] text-[var(--color-text-muted)]">
                  verified_at_runtime_by {safety.data.verified_at_runtime_by}
                </p>
              </Card>
            </>
          )}
        </div>
      )}

      {tab === 'users' && can('user:manage') && (
        <UserManagement users={users} cases={cases} notify={notify} />
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
          alert
            ? 'border-[var(--color-warning)] text-[var(--color-warning)]'
            : 'border-[var(--color-border)] text-[var(--color-text-muted)]'
        }`}>
          <Icon name={icon} size={14} />
        </span>
      </div>
      <p className="data-num mt-2 text-[22px] font-semibold leading-none text-[var(--color-primary-deep)]">{value}</p>
      {hint && <p className="mt-1.5 text-[12px] leading-snug text-[var(--color-text-muted)]">{hint}</p>}
    </div>
  )
}

function KV({ items }: { items: Array<[string, React.ReactNode]> }) {
  return (
    <dl className="divide-y divide-[var(--color-border)]">
      {items.map(([k, v]) => (
        <div key={k} className="grid grid-cols-[150px_1fr] gap-2 py-1.5">
          <dt className="text-[11.5px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">{k}</dt>
          <dd className="break-words text-[12.5px] text-[var(--color-text)]">{v}</dd>
        </div>
      ))}
    </dl>
  )
}

function UserManagement({ users, cases, notify }: { users: any; cases: any[]; notify: any }) {
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [form, setForm] = useState({
    user_id: '', display_name: '', role: 'ANALYST', password: '', unit: '', case_access: [] as string[],
  })

  async function createUser() {
    setErr(null)
    if (!/^[A-Za-z]{3}-\d{3,4}$/.test(form.user_id.trim())) { setErr('User ID must look like ANL-3311.'); return }
    if (form.display_name.trim().length < 2) { setErr('Display name is required.'); return }
    if (form.password.length < 6) { setErr('Password must be at least 6 characters.'); return }
    setBusy(true)
    try {
      await api.post('/api/security/users', { ...form, user_id: form.user_id.trim().toUpperCase() })
      notify('success', 'User created', `${form.user_id.toUpperCase()} provisioned with role ${form.role}.`)
      setOpen(false)
      setForm({ user_id: '', display_name: '', role: 'ANALYST', password: '', unit: '', case_access: [] })
      users.reload()
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : 'The user could not be created.')
    } finally { setBusy(false) }
  }

  async function patch(userId: string, body: any, label: string) {
    try {
      await api.patch(`/api/security/users/${userId}`, body)
      notify('success', 'User updated', `${userId}: ${label}`)
      users.reload()
    } catch (e) {
      notify('error', 'Update failed', e instanceof ApiError ? e.message : undefined)
    }
  }

  return (
    <Card solid title="Users, roles and case permissions" icon="user"
      subtitle="Changes take effect on the next authenticated request and are written to the audit trail."
      actions={<Button size="sm" variant="primary" icon="plus" onClick={() => setOpen(true)}>Create user</Button>}>
      {users.loading && <LoadingBlock label="Loading users…" variant="table" />}
      {users.error && <ErrorState message={users.error} onRetry={users.reload} />}
      {!users.loading && (users.data?.users || []).length === 0 && (
        <EmptyState title="No user accounts returned for your scope" icon="user" />
      )}
      {(users.data?.users || []).length > 0 && (
        <div className="-mx-5 overflow-x-auto">
          <table className="w-full min-w-[760px] text-left text-[12.5px]">
            <thead>
              <tr>
                {['User', 'Unit', 'Role', 'Case access', 'State', ''].map((h, i) => (
                  <th key={h + i} className="border-b border-[var(--color-border)] bg-[var(--color-primary-soft)] px-2.5 py-2 text-[10.5px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(users.data?.users || []).map((u: any) => (
                <tr key={u.user_id} className="border-b border-[var(--color-border)] last:border-0 hover:bg-[var(--color-primary-soft)]/50">
                  <td className="px-2.5 py-1.5">
                    <span className="mono-id font-semibold text-[var(--color-primary-deep)]">{u.user_id}</span>
                    <span className="block text-[11.5px] text-[var(--color-text-muted)]">{u.display_name}</span>
                  </td>
                  <td className="px-2.5 py-1.5 text-[var(--color-text-muted)]">{u.unit || '—'}</td>
                  <td className="px-2.5 py-1.5">
                    <Select value={u.role} className="!py-1 !text-[12px]"
                      onChange={(e) => patch(u.user_id, { role: e.target.value }, `role set to ${e.target.value}`)}>
                      {['INVESTIGATOR', 'ANALYST', 'SUPERVISOR', 'ADMIN'].map((r) => <option key={r} value={r}>{r}</option>)}
                    </Select>
                  </td>
                  <td className="mono-id px-2.5 py-1.5 text-[11px] text-[var(--color-text)]">{(u.case_access || []).join(', ') || '—'}</td>
                  <td className="px-2.5 py-1.5"><StatusPill status={u.active === false ? 'REJECTED' : 'VERIFIED'}
                    label={u.active === false ? 'DISABLED' : 'ACTIVE'} /></td>
                  <td className="px-2.5 py-1.5">
                    <Button size="sm" icon={u.active === false ? 'check' : 'lock'}
                      onClick={() => patch(u.user_id, { active: u.active === false }, u.active === false ? 're-enabled' : 'disabled')}>
                      {u.active === false ? 'Enable' : 'Disable'}
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Modal open={open} onClose={() => setOpen(false)} title="Create user" subtitle="Provision an account with least-privilege access"
        footer={<><Button onClick={() => setOpen(false)}>Cancel</Button><Button variant="primary" icon="plus" loading={busy} onClick={createUser}>Create user</Button></>}>
        {err && <p className="mb-2 rounded-[10px] border border-[var(--color-danger)] bg-[rgba(196,52,31,0.06)] px-3 py-2 text-[12.5px] text-[var(--color-danger)]">{err}</p>}
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <Field label="User ID" required hint="Format: ANL-3311">
            <TextInput value={form.user_id} onChange={(e) => setForm({ ...form, user_id: e.target.value })} placeholder="ANL-3311" className="mono-id" />
          </Field>
          <Field label="Display name" required>
            <TextInput value={form.display_name} onChange={(e) => setForm({ ...form, display_name: e.target.value })} placeholder="Officer name" />
          </Field>
          <Field label="Role" required>
            <Select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
              {['INVESTIGATOR', 'ANALYST', 'SUPERVISOR', 'ADMIN'].map((r) => <option key={r} value={r}>{r}</option>)}
            </Select>
          </Field>
          <Field label="Unit">
            <TextInput value={form.unit} onChange={(e) => setForm({ ...form, unit: e.target.value })} placeholder="Crime Records Bureau" />
          </Field>
          <Field label="Initial password" required hint="PBKDF2-HMAC-SHA256, 120k rounds, per-user salt.">
            <TextInput type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
          </Field>
          <Field label="Case access" hint="Leave empty for no case scope; supervisors/admins are unrestricted.">
            <div className="flex flex-wrap gap-1.5 pt-1">
              {cases.map((c: any) => {
                const on = form.case_access.includes(c.case_id)
                return (
                  <button key={c.case_id} type="button" aria-pressed={on}
                    onClick={() => setForm({
                      ...form,
                      case_access: on ? form.case_access.filter((x) => x !== c.case_id) : [...form.case_access, c.case_id],
                    })}
                    className={`focus-ring mono-id rounded-md px-2 py-1 text-[11px] font-semibold transition ${
                      on
                        ? 'bg-[var(--color-primary)] text-white'
                        : 'border border-[var(--color-border)] bg-[var(--color-surface-solid)] text-[var(--color-text)]'
                    }`}>
                    {c.case_id}
                  </button>
                )
              })}
            </div>
          </Field>
        </div>
      </Modal>
    </Card>
  )
}
