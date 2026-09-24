import { useEffect, useRef, useState } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

export interface MapPoint {
  location_id: string
  label: string
  lat: number
  lon: number
  cases: string[]
  event_count: number
  entities: Array<{ id: string; label: string; entity_type: string }>
  convergence?: any[]
}

interface Props {
  points: MapPoint[]
  height?: number
  selectedId?: string | null
  showHeat?: boolean
  showLinks?: boolean
  onSelect?: (id: string) => void
}

/**
 * Leaflet map rendered imperatively through a ref (no React wrapper library).
 * Tiles: OpenStreetMap raster tiles.
 */
export default function MapView({
  points, height = 520, selectedId = null, showHeat = true, showLinks = false, onSelect,
}: Props) {
  const [tilesUnavailable, setTilesUnavailable] = useState(false)
  const containerRef = useRef<HTMLDivElement | null>(null)
  const mapRef = useRef<L.Map | null>(null)
  const layerRef = useRef<L.LayerGroup | null>(null)
  const markerIndex = useRef<Record<string, L.CircleMarker>>({})

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return
    const map = L.map(containerRef.current, {
      center: [13.0827, 80.2707], zoom: 7, zoomControl: true, attributionControl: true,
      scrollWheelZoom: true,
    })
    const layer = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 18,
      attribution: '&copy; OpenStreetMap contributors',
      errorTileUrl: 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7',
    })
    // A map is the one component here that needs the network. If the basemap cannot be
    // fetched we say so instead of showing an empty panel that looks like missing data:
    // the evidence markers and their coordinates are drawn from the API either way.
    layer.on('tileerror', () => setTilesUnavailable(true))
    layer.on('load', () => setTilesUnavailable(false))
    layer.addTo(map)
    mapRef.current = map
    layerRef.current = L.layerGroup().addTo(map)
    return () => { map.remove(); mapRef.current = null }
  }, [])

  useEffect(() => {
    const map = mapRef.current
    const layer = layerRef.current
    if (!map || !layer) return
    layer.clearLayers()
    markerIndex.current = {}
    if (!points.length) return

    const maxEvents = Math.max(1, ...points.map((p) => p.event_count))

    if (showLinks) {
      const byCase: Record<string, MapPoint[]> = {}
      points.forEach((p) => p.cases.forEach((c) => { (byCase[c] ||= []).push(p) }))
      Object.entries(byCase).forEach(([, group]) => {
        if (group.length < 2) return
        const coords = group.map((p) => [p.lat, p.lon]) as [number, number][]
        L.polyline(coords, { color: '#2563eb', weight: 1.6, opacity: 0.45, dashArray: '5 6' }).addTo(layer)
      })
    }

    points.forEach((p) => {
      const intensity = p.event_count / maxEvents
      const hasConvergence = (p.convergence?.length || 0) > 0
      if (showHeat && p.event_count > 0) {
        L.circle([p.lat, p.lon], {
          radius: 2500 + intensity * 9000,
          color: hasConvergence ? '#f59e0b' : '#3b82f6',
          fillColor: hasConvergence ? '#fbbf24' : '#60a5fa',
          fillOpacity: 0.14 + intensity * 0.16,
          weight: 1,
        }).addTo(layer)
      }
      const marker = L.circleMarker([p.lat, p.lon], {
        radius: 7 + intensity * 7,
        color: '#ffffff',
        weight: 2,
        fillColor: p.event_count === 0 ? '#94a3b8' : hasConvergence ? '#f59e0b' : '#2563eb',
        fillOpacity: 0.95,
      }).addTo(layer)

      const entityList = p.entities.slice(0, 6).map((e) => `${e.label} <span style="opacity:.6">(${e.entity_type})</span>`).join('<br/>')
      marker.bindPopup(
        `<div style="font-family:Inter,system-ui,sans-serif;min-width:190px">
           <div style="font-weight:700;color:#102a52;font-size:13px">${p.label}</div>
           <div style="font-size:11px;color:#475569;margin-bottom:4px">${p.location_id} · ${p.lat.toFixed(4)}, ${p.lon.toFixed(4)}</div>
           <div style="font-size:11.5px;color:#0f172a"><b>${p.event_count}</b> evidence-backed event(s)</div>
           <div style="font-size:11.5px;color:#0f172a">Cases: ${p.cases.join(', ') || '—'}</div>
           ${hasConvergence ? '<div style="font-size:11.5px;color:#92400e;margin-top:3px">Potential convergence recorded here</div>' : ''}
           ${entityList ? `<div style="font-size:11px;color:#334155;margin-top:5px">${entityList}</div>` : ''}
           <div style="font-size:10px;color:#64748b;margin-top:6px">SYNTHETIC DEMONSTRATION DATA</div>
         </div>`,
      )
      marker.on('click', () => onSelect?.(p.location_id))
      markerIndex.current[p.location_id] = marker
    })

    const bounds = L.latLngBounds(points.map((p) => [p.lat, p.lon] as [number, number]))
    map.fitBounds(bounds, { padding: [45, 45], maxZoom: 11 })
  }, [points, showHeat, showLinks, onSelect])

  useEffect(() => {
    const map = mapRef.current
    if (!map || !selectedId) return
    const marker = markerIndex.current[selectedId]
    if (!marker) return
    map.setView(marker.getLatLng(), Math.max(map.getZoom(), 11), { animate: true })
    marker.openPopup()
  }, [selectedId])

  useEffect(() => {
    const map = mapRef.current
    if (!map) return
    const t = setTimeout(() => map.invalidateSize(), 220)
    return () => clearTimeout(t)
  }, [height])

  return (
    <div className="relative">
      <div
        ref={containerRef}
        style={{ height }}
        className="w-full overflow-hidden rounded-[12px] border border-[var(--color-border)] bg-[var(--color-primary-soft)]"
      />
      {tilesUnavailable && (
        <p className="mt-2 flex items-start gap-2 rounded-[10px] border border-dashed border-[var(--color-text-muted)] px-3 py-2 text-[11.5px] leading-relaxed text-[var(--color-text-muted)]">
          <span className="font-semibold uppercase tracking-wide">Basemap unavailable</span>
          <span>— raster tiles could not be fetched from the network. The evidence markers, coordinates and
            convergence links below are drawn from the case API and remain accurate.</span>
        </p>
      )}
    </div>
  )
}
