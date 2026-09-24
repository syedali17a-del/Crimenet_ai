import { useEffect, useMemo, useRef } from 'react'
import cytoscape from 'cytoscape'
import type { Core, ElementDefinition } from 'cytoscape'
import type { GraphPayload } from '../../types'
import { entityTone } from '../shared/ui'

export interface GraphFilters {
  search: string
  entityTypes: string[]
  caseId: string | null
  relationshipTypes: string[]
  supportLevels: string[]
  verifiedOnly: boolean
  dateFrom?: string
  dateTo?: string
}

export const DEFAULT_FILTERS: GraphFilters = {
  search: '', entityTypes: [], caseId: null, relationshipTypes: [],
  supportLevels: [], verifiedOnly: false,
}

export function filterPayload(payload: GraphPayload | null, f: GraphFilters): GraphPayload | null {
  if (!payload) return null
  const q = f.search.trim().toLowerCase()
  let nodes = payload.nodes
  if (f.entityTypes.length) nodes = nodes.filter((n) => f.entityTypes.includes(n.data.entity_type))
  if (f.caseId) nodes = nodes.filter((n) => (n.data.cases || []).includes(f.caseId!))
  const ids = new Set(nodes.map((n) => n.data.id))

  let edges = payload.edges.filter((e) => ids.has(e.data.source) && ids.has(e.data.target))
  if (f.relationshipTypes.length) edges = edges.filter((e) => f.relationshipTypes.includes(e.data.relationship_type))
  if (f.supportLevels.length) edges = edges.filter((e) => f.supportLevels.includes(e.data.support_level))
  if (f.verifiedOnly) edges = edges.filter((e) => e.data.verification_status === 'HUMAN_VERIFIED')
  if (f.dateFrom) edges = edges.filter((e) => !e.data.timestamp || e.data.timestamp >= f.dateFrom!)
  if (f.dateTo) edges = edges.filter((e) => !e.data.timestamp || e.data.timestamp <= `${f.dateTo!}T23:59:59Z`)

  if (q) {
    const matched = new Set(nodes.filter((n) => n.data.label?.toLowerCase().includes(q) || n.data.id.toLowerCase().includes(q)).map((n) => n.data.id))
    const keep = new Set(matched)
    edges.forEach((e) => {
      if (matched.has(e.data.source)) keep.add(e.data.target)
      if (matched.has(e.data.target)) keep.add(e.data.source)
    })
    nodes = nodes.filter((n) => keep.has(n.data.id))
    const keepIds = new Set(nodes.map((n) => n.data.id))
    edges = edges.filter((e) => keepIds.has(e.data.source) && keepIds.has(e.data.target))
  }

  return { ...payload, nodes, edges, counts: { nodes: nodes.length, edges: edges.length } }
}

/* Canvas colours mirror the design tokens in src/index.css — cytoscape needs
   literal values, so they are repeated here and nowhere else. */
const SUPPORT_COLOR: Record<string, string> = {
  HIGH: '#1E8E5A', MEDIUM: '#B8791A', LOW: '#5B6B85', INSUFFICIENT: '#C4341F',
}

const COMMUNITY_COLORS = ['#1450C4', '#2FA7DB', '#1E8E5A', '#B8791A', '#5B3FA8', '#A03A6B', '#5B6B85', '#0B2F73']

export default function NetworkGraph({
  payload, onReady, onSelectNode, onSelectEdge, onBackgroundClick,
  highlightPath = [], communities = {}, showCommunities = false, height = 520,
}: {
  payload: GraphPayload | null
  onReady?: (cy: Core) => void
  onSelectNode?: (id: string) => void
  onSelectEdge?: (id: string) => void
  onBackgroundClick?: () => void
  highlightPath?: string[]
  communities?: Record<string, number>
  showCommunities?: boolean
  height?: number | string
}) {
  const container = useRef<HTMLDivElement>(null)
  const cyRef = useRef<Core | null>(null)

  const elements: ElementDefinition[] = useMemo(() => {
    if (!payload) return []
    return [
      ...payload.nodes.map((n) => ({
        data: {
          ...n.data,
          size: Math.min(58, 26 + (n.data.degree || 0) * 3.4),
          color: showCommunities && communities[n.data.id] !== undefined
            ? COMMUNITY_COLORS[communities[n.data.id] % COMMUNITY_COLORS.length]
            : entityTone[n.data.entity_type] || '#5B6B85',
        },
      })),
      ...payload.edges.map((e) => ({ data: { ...e.data } })),
    ]
  }, [payload, showCommunities, communities])

  useEffect(() => {
    if (!container.current) return
    const cy = cytoscape({
      container: container.current,
      elements,
      wheelSensitivity: 0.22,
      minZoom: 0.15,
      maxZoom: 3.2,
      style: [
        {
          selector: 'node',
          style: {
            'background-color': 'data(color)',
            label: 'data(label)',
            color: '#0B2F73',
            'font-size': 10,
            'font-weight': 600,
            'font-family': 'ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, sans-serif',
            'text-valign': 'bottom',
            'text-margin-y': 5,
            'text-max-width': '92px',
            'text-wrap': 'ellipsis',
            width: 'data(size)',
            height: 'data(size)',
            'border-width': 2,
            'border-color': '#ffffff',
            'overlay-opacity': 0,
            'transition-property': 'background-color, border-color, opacity, width, height',
            'transition-duration': 180 as any,
          },
        },
        {
          selector: 'node[verification_status = "HUMAN_VERIFIED"]',
          style: { 'border-color': '#1E8E5A', 'border-width': 3 },
        },
        {
          selector: 'node[verification_status = "REJECTED"]',
          style: { 'border-color': '#C4341F', 'border-style': 'dashed', opacity: 0.6 },
        },
        {
          selector: 'node[entity_type = "CASE"]',
          style: { shape: 'round-rectangle', 'background-color': '#0B2F73', color: '#0B2F73' },
        },
        { selector: 'node[entity_type = "VEHICLE"]', style: { shape: 'round-hexagon' } },
        { selector: 'node[entity_type = "LOCATION"]', style: { shape: 'round-diamond' } },
        { selector: 'node[entity_type = "ACCOUNT"]', style: { shape: 'round-tag' } },
        { selector: 'node[entity_type = "ORGANIZATION"]', style: { shape: 'round-pentagon' } },
        {
          selector: 'edge',
          style: {
            width: 1.7,
            'line-color': (e: any) => SUPPORT_COLOR[e.data('support_level')] || '#5B6B85',
            'target-arrow-color': (e: any) => SUPPORT_COLOR[e.data('support_level')] || '#5B6B85',
            'target-arrow-shape': 'triangle',
            'arrow-scale': 0.8,
            'curve-style': 'bezier',
            label: 'data(relationship_type)',
            'font-size': 8,
            'font-weight': 600,
            color: '#5B6B85',
            'text-background-color': '#ffffff',
            'text-background-opacity': 0.95,
            'text-background-padding': 1.5 as any,
            'text-rotation': 'autorotate',
            opacity: 0.85,
          },
        },
        {
          selector: 'edge[verification_status = "HUMAN_VERIFIED"]',
          style: { width: 3, opacity: 1 },
        },
        {
          selector: 'edge[verification_status = "UNVERIFIED"]',
          style: { 'line-style': 'dashed' },
        },
        {
          selector: 'edge[verification_status = "REJECTED"]',
          style: { 'line-style': 'dotted', opacity: 0.4 },
        },
        {
          selector: '.faded',
          style: { opacity: 0.12, 'text-opacity': 0.08 },
        },
        {
          selector: '.path-highlight',
          style: {
            'line-color': '#1a6adb', 'target-arrow-color': '#1a6adb', width: 4.5,
            'border-color': '#1a6adb', 'border-width': 4, opacity: 1, 'z-index': 99,
          },
        },
        {
          selector: ':selected',
          style: { 'border-color': '#1257c4', 'border-width': 4, 'line-color': '#1257c4', 'target-arrow-color': '#1257c4' },
        },
      ],
      layout: { name: 'cose', animate: false, padding: 40, nodeRepulsion: 12000, idealEdgeLength: 110, nodeDimensionsIncludeLabels: true } as any,
    })

    cy.on('tap', 'node', (evt) => onSelectNode?.(evt.target.id()))
    cy.on('tap', 'edge', (evt) => onSelectEdge?.(evt.target.id()))
    cy.on('tap', (evt) => { if (evt.target === cy) onBackgroundClick?.() })
    cy.on('mouseover', 'node', () => { if (container.current) container.current.style.cursor = 'pointer' })
    cy.on('mouseout', 'node', () => { if (container.current) container.current.style.cursor = 'default' })

    cyRef.current = cy
    onReady?.(cy)
    return () => { cy.destroy(); cyRef.current = null }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [elements])

  useEffect(() => {
    const cy = cyRef.current
    if (!cy) return
    cy.elements().removeClass('path-highlight faded')
    if (highlightPath.length > 1) {
      cy.elements().addClass('faded')
      highlightPath.forEach((id, i) => {
        const node = cy.getElementById(id)
        node.removeClass('faded').addClass('path-highlight')
        if (i > 0) {
          cy.edges().filter((e) =>
            (e.data('source') === highlightPath[i - 1] && e.data('target') === id) ||
            (e.data('target') === highlightPath[i - 1] && e.data('source') === id),
          ).removeClass('faded').addClass('path-highlight')
        }
      })
    }
  }, [highlightPath])

  return (
    <div
      ref={container}
      style={{ height }}
      className="w-full rounded-[12px] border border-[var(--color-border)] bg-[var(--color-surface-solid)]"
      role="application"
      aria-label="Evidence network graph"
    />
  )
}
