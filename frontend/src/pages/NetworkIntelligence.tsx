import { useMemo, useRef, useState } from 'react'
import type { Core } from 'cytoscape'
import { useApp } from '../state/AppContext'
import { useFetch } from '../hooks/useFetch'
import { api, ApiError } from '../services/api'
import NetworkGraph, { DEFAULT_FILTERS, filterPayload } from '../components/graph/NetworkGraph'
import EntityPanel, { RelationshipPanel } from '../components/graph/EntityPanel'
import type { GraphFilters } from '../components/graph/NetworkGraph'
import type { GraphPayload } from '../types'
import { Icon } from '../components/shared/Icon'
import {
  Button, Card, EmptyState, ErrorState, InsufficientEvidence, LoadingBlock, PageHeader,
  SectionHeader, Select, TextInput,
} from '../components/shared/ui'
import { useI18n } from '../i18n/LanguageContext'

/* ============================================================================
   NETWORK INTELLIGENCE
   The graph canvas is drawn on a SOLID surface: a working chart must not sit on
   a blurred panel. Glass is used only where the spec allows it here — the filter
   control panel and the inspector drawer that slides over the canvas.
   ============================================================================ */

const ENTITY_TYPES = ['PERSON', 'ALIAS', 'VEHICLE', 'PHONE', 'ACCOUNT', 'LOCATION', 'ORGANIZATION', 'DEVICE', 'CASE']
const REL_TYPES = ['ASSOCIATED_WITH', 'USED', 'LOCATED_AT', 'CONNECTED_TO', 'PART_OF', 'MENTIONED_IN', 'TRANSACTED_WITH', 'OBSERVED_AT', 'RELATED_TO']
const SUPPORTS = ['HIGH', 'MEDIUM', 'LOW']

export default function NetworkIntelligence() {
  const { t } = useI18n()
  const { activeCase, cases, notify, can } = useApp()
  const cyRef = useRef<Core | null>(null)
  const [filters, setFilters] = useState<GraphFilters>({ ...DEFAULT_FILTERS, caseId: activeCase })
  const [selectedNode, setSelectedNode] = useState<string | null>(null)
  const [selectedEdge, setSelectedEdge] = useState<string | null>(null)
  const [showCommunities, setShowCommunities] = useState(false)
  const [path, setPath] = useState<{ from: string; to: string }>({ from: '', to: '' })
  const [pathNodes, setPathNodes] = useState<string[]>([])
  const [pathInfo, setPathInfo] = useState<any>(null)
  const [analysis, setAnalysis] = useState<any>(null)
  const [analysing, setAnalysing] = useState(false)

  const graph = useFetch<GraphPayload>(`/api/graph${activeCase ? `?case_id=${activeCase}` : ''}`, [activeCase])
  const filtered = useMemo(() => filterPayload(graph.data, filters), [graph.data, filters])

  const communities = useMemo(() => {
    const map: Record<string, number> = {}
    ;(analysis?.communities || []).forEach((c: any) => c.members.forEach((m: any) => { map[m.id] = c.community_id }))
    return map
  }, [analysis])

  /** A2 — the per-node structural explanation produced by the backend, indexed by node id. */
  const explanations = useMemo(() => {
    const map: Record<string, { degree?: string; betweenness?: string; score?: string }> = {}
    ;(analysis?.degree_centrality || []).forEach((row: any) => {
      map[row.entity_id] = { ...(map[row.entity_id] || {}), degree: row.interpretation, score: row.score }
    })
    ;(analysis?.betweenness_centrality || []).forEach((row: any) => {
      map[row.entity_id] = { ...(map[row.entity_id] || {}), betweenness: row.interpretation, score: row.score }
    })
    return map
  }, [analysis])

  const nodeOptions = useMemo(
    () => (graph.data?.nodes || []).map((n) => ({ id: n.data.id, label: `${n.data.label} (${n.data.entity_type})` })),
    [graph.data],
  )

  async function runAnalysis() {
    setAnalysing(true)
    try {
      const res = await api.post<any>('/api/analysis/network', { case_ids: activeCase ? [activeCase] : [] })
      setAnalysis(res)
      notify(res.sufficient ? 'success' : 'info', 'Network analysis complete',
        res.sufficient ? `${res.nodes} nodes · ${res.edges} edges · ${res.communities.length} clusters (${res.engine})` : res.message)
    } catch (err) {
      notify('error', 'Network analysis failed', err instanceof ApiError ? err.message : undefined)
    } finally { setAnalysing(false) }
  }

  async function runPath() {
    if (!path.from || !path.to) { notify('info', 'Select both endpoints for the path analysis'); return }
    try {
      const res = await api.post<any>('/api/analysis/shortest-path', {
        source: path.from, target: path.to, case_ids: activeCase ? [activeCase] : [],
      })
      setPathInfo(res)
      if (res.found) {
        setPathNodes(res.path_ids)
        notify('success', `Path found (${res.length} hop(s))`, res.nodes.map((n: any) => n.label).join(' → '))
      } else {
        setPathNodes([])
        notify('info', 'No evidence-backed path', res.message)
      }
    } catch (err) {
      notify('error', 'Path analysis failed', err instanceof ApiError ? err.message : undefined)
    }
  }

  function toggle(list: string[], value: string): string[] {
    return list.includes(value) ? list.filter((v) => v !== value) : [...list, value]
  }

  return (
    <>
      <PageHeader
        tagline={t.pages.network.tagline}
        title={t.pages.network.title}
        description={t.pages.network.description}
      >
        <Button icon="refresh" onClick={graph.reload}>{t.analysis.net.reload}</Button>
        {can('analysis:run') && (
          <Button variant="primary" icon="spark" loading={analysing} onClick={runAnalysis}>{t.analysis.net.runAnalysis}</Button>
        )}
      </PageHeader>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-[1fr_380px]">
        <div className="space-y-5">
          {/* ── filter / path control panel (glass, per spec) ─────────────── */}
          <Card
            title={t.analysis.net.controls}
            icon="filter"
            actions={
              <>
                <Button size="sm" icon="fit" onClick={() => cyRef.current?.fit(undefined, 45)}>{t.analysis.net.fit}</Button>
                <Button size="sm" icon="reset" onClick={() => {
                  setFilters({ ...DEFAULT_FILTERS, caseId: activeCase }); setPathNodes([]); setPathInfo(null)
                  setSelectedEdge(null); setSelectedNode(null)
                  cyRef.current?.layout({ name: 'cose', animate: false, padding: 40 } as any).run()
                }}>{t.analysis.net.reset}</Button>
              </>
            }
          >
            {/* BUG 4: the four fields own one cell each, so the two date inputs are no
                longer squeezed into a single column beside the checkbox label. */}
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
              <TextInput placeholder={t.analysis.net.searchEntity} value={filters.search}
                onChange={(e) => setFilters({ ...filters, search: e.target.value })} />
              <Select value={filters.caseId || ''} onChange={(e) => setFilters({ ...filters, caseId: e.target.value || null })}>
                <option value="">{t.analysis.net.allAuthorizedCases}</option>
                {cases.map((c) => <option key={c.case_id} value={c.case_id}>{c.case_id}</option>)}
              </Select>
              <TextInput type="date" value={filters.dateFrom || ''} aria-label={t.analysis.tl.startDate}
                onChange={(e) => setFilters({ ...filters, dateFrom: e.target.value })} />
              <TextInput type="date" value={filters.dateTo || ''} aria-label={t.analysis.tl.endDate}
                onChange={(e) => setFilters({ ...filters, dateTo: e.target.value })} />
            </div>

            {/* BUG 4: structurally independent of the field grid above — the checkbox
                can never compete for column space with the date inputs at any breakpoint. */}
            <div className="mt-3">
              <label className="flex w-fit items-center gap-2 text-[12.5px] font-semibold text-[var(--color-text)]">
                <input type="checkbox" checked={filters.verifiedOnly} className="h-4 w-4 accent-[var(--color-primary)]"
                  onChange={(e) => setFilters({ ...filters, verifiedOnly: e.target.checked })} />
                {t.analysis.net.verifiedOnly}
              </label>
            </div>

            <div className="mt-4 space-y-2.5">
              <ChipRow label={t.analysis.net.entityType} kind="entityType" values={ENTITY_TYPES} selected={filters.entityTypes}
                onToggle={(v) => setFilters({ ...filters, entityTypes: toggle(filters.entityTypes, v) })} />
              <ChipRow label={t.analysis.net.relationship} kind="relationshipType" values={REL_TYPES} selected={filters.relationshipTypes}
                onToggle={(v) => setFilters({ ...filters, relationshipTypes: toggle(filters.relationshipTypes, v) })} />
              <ChipRow label={t.analysis.net.support} kind="supportLevel" values={SUPPORTS} selected={filters.supportLevels}
                onToggle={(v) => setFilters({ ...filters, supportLevels: toggle(filters.supportLevels, v) })} />
            </div>

            <div className="mt-4 grid grid-cols-1 gap-2 border-t border-[var(--color-border)] pt-4 md:grid-cols-[1fr_1fr_auto_auto]">
              <Select value={path.from} onChange={(e) => setPath({ ...path, from: e.target.value })}>
                <option value="">{t.analysis.net.pathFrom}</option>
                {nodeOptions.map((n) => <option key={n.id} value={n.id}>{n.label}</option>)}
              </Select>
              <Select value={path.to} onChange={(e) => setPath({ ...path, to: e.target.value })}>
                <option value="">{t.analysis.net.pathTo}</option>
                {nodeOptions.map((n) => <option key={n.id} value={n.id}>{n.label}</option>)}
              </Select>
              <Button size="sm" icon="branch" onClick={runPath}>{t.analysis.net.highlightPath}</Button>
              <Button size="sm" icon="eye" variant={showCommunities ? 'primary' : 'neu'}
                onClick={() => { if (!analysis) runAnalysis(); setShowCommunities((s) => !s) }}>
                {t.analysis.net.communities}
              </Button>
            </div>

            {pathInfo && (
              <div className={`mt-4 rounded-[12px] border px-3.5 py-2.5 text-[12.5px] ${
                pathInfo.found
                  ? 'border-[var(--color-primary)] bg-[var(--color-primary-soft)] text-[var(--color-text)]'
                  : 'border-dashed border-[var(--color-text-muted)] bg-[var(--color-surface-solid)] text-[var(--color-text)]'
              }`}>
                {pathInfo.found ? (
                  <>
                    <p className="font-semibold text-[var(--color-primary-deep)]">{pathInfo.nodes.map((n: any) => n.label).join('  →  ')}</p>
                    <p className="mt-1 text-[11.5px] text-[var(--color-text-muted)]">{pathInfo.interpretation}</p>
                  </>
                ) : <p>{pathInfo.message}</p>}
              </div>
            )}
          </Card>

          {/* ── graph canvas: SOLID surface ──────────────────────────────── */}
          <section className="surface-solid">
            <header className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--color-border)] px-5 py-3.5">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-[var(--color-primary)]"><Icon name="network" size={16} /></span>
                  <h2 className="section-header !text-[13px]">{t.analysis.net.graphTitle}</h2>
                </div>
                {filtered && (
                  <p className="mt-1 text-[12.5px] text-[var(--color-text-muted)]">
                    {t.analysis.net.graphSubtitle(filtered.counts.nodes, filtered.counts.edges)}
                  </p>
                )}
              </div>
              <Legend />
            </header>
            <div className="p-5">
              {graph.loading && <LoadingBlock label={t.analysis.net.reconstructing} rows={3} />}
              {graph.error && <ErrorState message={graph.error} onRetry={graph.reload} />}
              {graph.data && !graph.data.sufficient && <InsufficientEvidence message={graph.data.message} />}
              {filtered && filtered.counts.nodes > 0 && (
                <NetworkGraph
                  payload={filtered} height={540} onReady={(cy) => { cyRef.current = cy }}
                  onSelectNode={(id) => { setSelectedNode(id); setSelectedEdge(null) }}
                  onSelectEdge={(id) => { setSelectedEdge(id); setSelectedNode(null) }}
                  onBackgroundClick={() => { setSelectedNode(null); setSelectedEdge(null) }}
                  highlightPath={pathNodes} communities={communities} showCommunities={showCommunities}
                />
              )}
              {filtered && filtered.counts.nodes === 0 && graph.data?.sufficient && (
                <EmptyState title={t.analysis.net.noMatch} icon="filter"
                  action={<Button size="sm" icon="reset" onClick={() => setFilters({ ...DEFAULT_FILTERS, caseId: activeCase })}>{t.common.clearFilters}</Button>} />
              )}
            </div>
          </section>

          {/* ── structural rankings: the explainable A2 output ───────────── */}
          {analysis && analysis.sufficient && (
            <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
              <Card solid title={t.analysis.net.degree} icon="target" subtitle={t.analysis.net.degreeSub}>
                <RankList items={analysis.degree_centrality} onSelect={setSelectedNode} />
              </Card>
              <Card solid title={t.analysis.net.betweenness} icon="branch" subtitle={t.analysis.net.betweennessSub}>
                <RankList items={analysis.betweenness_centrality} onSelect={setSelectedNode} />
              </Card>
              <Card solid title={t.analysis.net.communities} icon="entities"
                subtitle={t.analysis.net.communitiesSub(analysis.community_algorithm, String(analysis.modularity ?? '—'))}>
                {analysis.communities.length === 0 ? (
                  <EmptyState title={t.analysis.net.noRanked} icon="entities" />
                ) : (
                  <ul className="space-y-2">
                    {analysis.communities.map((c: any) => (
                      <li key={c.community_id} className="rounded-[12px] border border-[var(--color-border)] px-3 py-2">
                        <p className="text-[12.5px] font-semibold text-[var(--color-primary-deep)]">
                          Cluster {c.community_id} · <span className="data-num">{c.size}</span> entities
                        </p>
                        <p className="mt-0.5 truncate text-[11.5px] text-[var(--color-text-muted)]">
                          {c.members.slice(0, 5).map((m: any) => m.label).join(', ')}{c.members.length > 5 ? '…' : ''}
                        </p>
                      </li>
                    ))}
                  </ul>
                )}
              </Card>
              <div className="lg:col-span-3">
                <p className="banner-honesty flex items-start gap-2 px-3.5 py-2.5 text-[12px]">
                  <Icon name="info" size={13} />
                  <span>
                    {analysis.safety_note} Engine: {analysis.engine}. Density <span className="data-num">{analysis.density}</span>;{' '}
                    <span className="data-num">{analysis.components}</span> connected component(s).
                  </span>
                </p>
              </div>
            </div>
          )}
          {analysis && !analysis.sufficient && <InsufficientEvidence message={analysis.message} />}
        </div>

        {/* ── inspector column: the drawer is glass, its content is not ──── */}
        <div className="xl:sticky xl:top-[112px] xl:h-[calc(100vh-152px)]">
          {selectedNode && (
            <EntityPanel
              entityId={selectedNode}
              onClose={() => setSelectedNode(null)}
              onSelectEntity={(id) => setSelectedNode(id)}
              onChanged={graph.reload}
              structuralExplanation={explanations[selectedNode]}
              analysisReady={Boolean(analysis?.sufficient)}
              onRunAnalysis={can('analysis:run') ? runAnalysis : undefined}
              analysing={analysing}
            />
          )}
          {selectedEdge && (
            <RelationshipPanel relationshipId={selectedEdge} onClose={() => setSelectedEdge(null)} onChanged={graph.reload} />
          )}
          {!selectedNode && !selectedEdge && (
            <Card title={t.analysis.net.inspector} icon="eye">
              <SectionHeader>{t.analysis.net.inspectorNode}</SectionHeader>
              <p className="text-[13px] leading-relaxed text-[var(--color-text-muted)]">
                {t.analysis.net.inspectorIntroA} <span className="font-semibold text-[var(--color-text)]">{t.analysis.net.inspectorNode}</span>{' '}
                {t.analysis.net.inspectorIntroB}
                <span className="font-semibold text-[var(--color-text)]"> {t.analysis.net.inspectorEdge}</span>{' '}
                {t.analysis.net.inspectorIntroC}
              </p>
              <ul className="mt-3 space-y-2">
                {t.analysis.net.inspectorTips.map((tip) => (
                  <li key={tip} className="flex items-start gap-2 text-[12.5px] text-[var(--color-text)]">
                    <span className="mt-0.5 text-[var(--color-primary)]"><Icon name="check" size={13} /></span>{tip}
                  </li>
                ))}
              </ul>
              {!analysis && can('analysis:run') && (
                <Button size="sm" variant="outline" className="mt-4 w-full" icon="spark" loading={analysing} onClick={runAnalysis}>
                  {t.analysis.net.runAnalysis}
                </Button>
              )}
            </Card>
          )}
        </div>
      </div>
    </>
  )
}

function ChipRow({ label, values, selected, onToggle, kind }: { label: string; values: string[]; selected: string[]; onToggle: (v: string) => void; kind: 'entityType' | 'relationshipType' | 'supportLevel' }) {
  const { t, tok } = useI18n()
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <span className="mr-1 text-[11px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">{label}</span>
      {values.map((v) => {
        const on = selected.includes(v)
        return (
          <button
            key={v}
            onClick={() => onToggle(v)}
            aria-pressed={on}
            className={`focus-ring rounded-md px-2 py-1 text-[11px] font-semibold transition ${
              on
                ? 'bg-[var(--color-primary)] text-white'
                : 'border border-[var(--color-border)] bg-[var(--color-surface-solid)] text-[var(--color-text)] hover:border-[var(--color-primary)]'
            }`}
          >
            {tok(t.tokens[kind], v)}
          </button>
        )
      })}
    </div>
  )
}

function RankList({ items, onSelect }: { items: any[]; onSelect: (id: string) => void }) {
  const { t } = useI18n()
  if (!items?.length) return <EmptyState title={t.analysis.net.noRanked} icon="target" />
  return (
    <ol className="space-y-2">
      {items.slice(0, 6).map((i) => (
        <li key={i.entity_id}>
          <button
            onClick={() => onSelect(i.entity_id)}
            className="focus-ring w-full rounded-[12px] border border-[var(--color-border)] bg-[var(--color-surface-solid)] px-3 py-2.5 text-left transition hover:border-[var(--color-primary)]"
          >
            <div className="flex items-center justify-between gap-2">
              <span className="truncate text-[12.5px] font-semibold text-[var(--color-text)]">
                <span className="data-num text-[var(--color-text-muted)]">{i.rank}.</span> {i.label}
              </span>
              <span className="data-num shrink-0 rounded-md bg-[var(--color-primary-soft)] px-1.5 py-0.5 text-[11.5px] font-semibold text-[var(--color-primary-deep)]">
                {i.score}
              </span>
            </div>
            <p className="mt-1 text-[11.5px] leading-snug text-[var(--color-text-muted)]">{i.interpretation}</p>
          </button>
        </li>
      ))}
    </ol>
  )
}

function Legend() {
  const { t } = useI18n()
  return (
    <div className="hidden flex-wrap items-center gap-3 text-[10.5px] font-semibold text-[var(--color-text-muted)] sm:flex">
      <span className="flex items-center gap-1.5">
        <span className="h-2 w-5 rounded" style={{ background: 'var(--color-success)' }} /> {t.analysis.net.legendHigh}
      </span>
      <span className="flex items-center gap-1.5">
        <span className="h-2 w-5 rounded" style={{ background: 'var(--color-warning)' }} /> {t.analysis.net.legendMedium}
      </span>
      <span className="flex items-center gap-1.5">
        <span className="h-2 w-5 rounded border border-[var(--color-text-muted)]" /> {t.analysis.net.legendLow}
      </span>
      <span className="flex items-center gap-1.5">
        <span className="h-0.5 w-5 border-t-2 border-dashed border-[var(--color-text-muted)]" /> {t.analysis.net.legendUnverified}
      </span>
    </div>
  )
}
