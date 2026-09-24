import { useMemo, useState } from 'react'
import { useApp } from '../state/AppContext'
import { useFetch } from '../hooks/useFetch'
import MapView from '../components/map/MapView'
import { Icon } from '../components/shared/Icon'
import {
  Badge, Button, Card, EmptyState, ErrorState, InsufficientEvidence, LoadingBlock, PageHeader, Select, SignalRow,
} from '../components/shared/ui'
import { useI18n } from '../i18n/LanguageContext'

export default function MapIntelligence() {
  const { t } = useI18n()
  const { cases, activeCase } = useApp()
  const [caseId, setCaseId] = useState(activeCase || '')
  const [selected, setSelected] = useState<string | null>(null)
  const [showHeat, setShowHeat] = useState(true)
  const [showLinks, setShowLinks] = useState(false)

  const { data, loading, error, reload } = useFetch<any>(
    `/api/map${caseId ? `?case_ids=${caseId}` : ''}`, [caseId],
  )

  const points = data?.points || []
  const selectedPoint = useMemo(() => points.find((p: any) => p.location_id === selected), [points, selected])

  return (
    <>
      <PageHeader
        tagline={t.pages.map.tagline}
        title={t.pages.map.title}
        description={t.pages.map.description}
      >
        <Button icon="refresh" onClick={reload}>Refresh</Button>
      </PageHeader>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1fr_340px]">
        <div className="space-y-4">
          <Card solid
            title="Evidence-linked locations" icon="map"
            subtitle={data ? `${data.count} geolocated location(s) in scope` : ''}
            actions={
              <div className="flex flex-wrap items-center gap-2">
                <Select value={caseId} onChange={(e) => setCaseId(e.target.value)} className="!py-1.5 !text-[12px]">
                  <option value="">All authorized cases</option>
                  {cases.map((c) => <option key={c.case_id} value={c.case_id}>{c.case_id}</option>)}
                </Select>
                <Button size="sm" variant={showHeat ? 'primary' : 'neu'} onClick={() => setShowHeat((s) => !s)}>Density</Button>
                <Button size="sm" variant={showLinks ? 'primary' : 'neu'} onClick={() => setShowLinks((s) => !s)}>Case links</Button>
              </div>
            }
          >
            {loading && <LoadingBlock label="Plotting evidence-linked locations…" rows={3} />}
            {error && <ErrorState message={error} onRetry={reload} />}
            {data && !data.sufficient && <InsufficientEvidence message={data.message} />}
            {data?.sufficient && (
              <>
                <MapView points={points} selectedId={selected} showHeat={showHeat} showLinks={showLinks} onSelect={setSelected} height={520} />
                <div className="mt-2 flex flex-wrap items-center gap-3 text-[11px] font-semibold text-[var(--color-text-muted)]/75">
                  <span className="flex items-center gap-1"><span className="h-2.5 w-2.5 rounded-full bg-[var(--color-primary)]" /> Evidence-backed location</span>
                  <span className="flex items-center gap-1"><span className="h-2.5 w-2.5 rounded-full bg-[var(--color-warning)]" /> Potential convergence recorded</span>
                  <span className="flex items-center gap-1"><span className="h-2.5 w-2.5 rounded-full bg-[var(--color-text-muted)]" /> No events in scope</span>
                  <span className="ml-auto">Tiles &copy; OpenStreetMap contributors</span>
                </div>
              </>
            )}
          </Card>

          {data?.sufficient && (
            <Card solid title="Potential spatio-temporal convergence" icon="target"
              subtitle={`${data.convergence_events.length} window(s) where multiple entities were recorded at one location`}>
              {data.convergence_events.length === 0 ? (
                <p className="text-[13px] text-[var(--color-text-muted)]">No convergence windows in this scope.</p>
              ) : (
                <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
                  {data.convergence_events.map((c: any, i: number) => (
                    <div key={i} className="rounded-[12px] border border-[var(--color-warning)] bg-[rgba(184,121,26,0.06)] px-4 py-3">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <p className="text-[13px] font-semibold text-[var(--color-primary-deep)]">{c.location_id} · {c.window_start.slice(0, 10)}</p>
                        <Badge tone="amber">{c.status}</Badge>
                      </div>
                      <p className="mt-0.5 text-[11.5px] text-[var(--color-text-muted)]">
                        {c.window_start.slice(11, 19)} → {c.window_end.slice(11, 19)} · Evidence {c.evidence_ids.join(', ')}
                      </p>
                      <ul className="mt-1.5">{c.signals.map((s: any, j: number) => <SignalRow key={j} signal={s} />)}</ul>
                      <p className="mt-1.5 text-[11.5px] text-[var(--color-text-muted)]">Entities: {c.entities.join(', ')}</p>
                      <p className="mt-1.5 rounded-lg bg-[rgba(184,121,26,0.10)] px-2.5 py-1.5 text-[11.5px] text-[var(--color-warning)]">{c.disclaimer}</p>
                      <Button size="sm" className="mt-2" icon="map" onClick={() => setSelected(c.location_id)}>Show on map</Button>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          )}
        </div>

        <div className="space-y-4 xl:sticky xl:top-[112px] xl:self-start">
          <Card solid title="Locations" icon="map" subtitle="Ranked by evidence-backed events">
            {points.length === 0 && (
              <EmptyState title={t.common.noData} message={t.common.noRecords} icon="map" />
            )}
            <ul className="space-y-1.5">
              {[...points].sort((a: any, b: any) => b.event_count - a.event_count).map((p: any) => (
                <li key={p.location_id}>
                  <button onClick={() => setSelected(p.location_id)}
                    className={`focus-ring w-full rounded-lg border px-3 py-2 text-left transition ${
                      selected === p.location_id ? 'border-[var(--color-primary)] bg-[var(--color-primary-soft)]' : 'border-[var(--color-border)] bg-[var(--color-surface-solid)] hover:bg-[var(--color-primary-soft)]/60'}`}>
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate text-[12.5px] font-semibold text-[var(--color-primary-deep)]">{p.label}</span>
                      <Badge tone={p.event_count ? 'blue' : 'slate'}>{p.event_count} ev</Badge>
                    </div>
                    <p className="text-[11px] text-[var(--color-text-muted)]/75">{p.location_id} · {p.cases.join(', ') || 'no case link'}</p>
                  </button>
                </li>
              ))}
            </ul>
          </Card>

          {selectedPoint && (
            <Card solid title={selectedPoint.label} icon="target" subtitle={`${selectedPoint.lat.toFixed(4)}, ${selectedPoint.lon.toFixed(4)}`}>
              <p className="text-[12px] text-[var(--color-text-muted)]/85">Cases: {selectedPoint.cases.join(', ') || '—'}</p>
              <p className="mt-0.5 text-[12px] text-[var(--color-text-muted)]/85">Evidence: {selectedPoint.evidence_ids?.join(', ') || '—'}</p>
              <p className="mt-2 text-[11px] font-bold uppercase tracking-wider text-[var(--color-text-muted)]/60">Entities recorded here</p>
              <div className="mt-1 flex flex-wrap gap-1.5">
                {selectedPoint.entities.length === 0 && <span className="text-[12px] text-[var(--color-text-muted)]/75">None</span>}
                {selectedPoint.entities.map((e: any) => (
                  <span key={e.id} className="rounded-md bg-[var(--color-primary-soft)] px-2 py-1 text-[11px] font-semibold text-[var(--color-text)] ring-1 ring-[var(--color-primary)]">
                    {e.label}
                  </span>
                ))}
              </div>
              <p className="mt-2 text-[11px] font-bold uppercase tracking-wider text-[var(--color-text-muted)]/60">Events</p>
              <ul className="mt-1 max-h-52 space-y-1 overflow-y-auto pr-1">
                {selectedPoint.events.map((e: any) => (
                  <li key={e.event_id} className="rounded-md bg-[var(--color-surface-solid)] px-2.5 py-1.5 text-[11.5px] text-[var(--color-text)] ring-1 ring-[rgba(147,194,251,0.4)]">
                    <span className="font-semibold">{e.timestamp.replace('T', ' ').replace('Z', '')}</span> — {e.title}
                    <span className="block text-[10.5px] text-[var(--color-text-muted)]/70">{e.case_id} · {e.evidence_id || 'no evidence id'}</span>
                  </li>
                ))}
              </ul>
            </Card>
          )}

          <Card solid title="Interpretation limits" icon="shield">
            <ul className="space-y-1.5 text-[12px] text-[var(--color-text)]">
              {[
                'Co-location in time is a lead, not proof that individuals met.',
                'Absence of a marker means absence of evidence, not absence of activity.',
                'No predictive hot-spot policing is performed by this platform.',
              ].map((t) => (
                <li key={t} className="flex items-start gap-1.5"><span className="mt-0.5 text-[var(--color-primary)]"><Icon name="info" size={13} /></span>{t}</li>
              ))}
            </ul>
          </Card>
        </div>
      </div>
    </>
  )
}
