import { GeoJSON as GeoJSONLayer, MapContainer, Popup, TileLayer, useMap } from 'react-leaflet'
import { latLngBounds } from 'leaflet'
import { useEffect, useMemo } from 'react'
import { Box, Typography } from '@mui/material'
import 'leaflet/dist/leaflet.css'
import { positionsFor } from './mapGeometry'

type Area = { id: string; name: string; geometry?: GeoJSON.Geometry | null; country?: string; level?: number }
type Signal = { area_id: string; severity?: string; name: string; probability?: number }

const kenyaCenter: [number, number] = [0.75, 34.6]

const severityColor = (severity = '') => {
  const normalized = severity.toLowerCase()
  if (['severe', 'high', 'go'].includes(normalized)) return '#b71c1c'
  if (['moderate', 'set', 'watch'].includes(normalized)) return '#ed6c02'
  return '#1b5e20'
}

function FitAffectedAreas({ areas }: { areas: Area[] }) {
  const map = useMap()
  useEffect(() => {
    const points = areas.flatMap((area) => (area.geometry ? positionsFor(area.geometry) : []).map(([lng, lat]) => [lat, lng] as [number, number]))
    if (points.length) map.fitBounds(latLngBounds(points), { padding: [30, 30], maxZoom: 8 })
    else map.setView(kenyaCenter, 6)
    const frame = window.requestAnimationFrame(() => map.invalidateSize())
    return () => window.cancelAnimationFrame(frame)
  }, [areas, map])
  return null
}

export function AreaMap({ areas, signals, onAreaSelect, height = 300 }: { areas: Area[]; signals: Signal[]; onAreaSelect?: (area: Area) => void; height?: number }) {
  // The admin-1 index is fetched without geometry (it would be megabytes per
  // country), so only draw the areas whose geometry has actually been loaded.
  const drawable = useMemo(() => areas.filter((area) => area.geometry), [areas])
  const affectedAreas = useMemo(() => drawable.map((area) => {
    const areaSignals = signals.filter((signal) => signal.area_id === area.id)
    const topSeverity = areaSignals.map((signal) => signal.severity || '').sort((a, b) => severityColor(b).localeCompare(severityColor(a)))[0]
    return { area, color: severityColor(topSeverity), signalCount: areaSignals.length }
  }), [drawable, signals])

  return <Box sx={{ position: 'relative', height, borderRadius: 1, overflow: 'hidden', border: 1, borderColor: 'divider', bgcolor: '#dbeafe' }}>
    <MapContainer center={kenyaCenter} zoom={6} minZoom={4} maxZoom={14} scrollWheelZoom zoomControl style={{ height: '100%', width: '100%' }} aria-label="Interactive OpenStreetMap of affected areas">
      <TileLayer attribution="&copy; <a href=&quot;https://www.openstreetmap.org/copyright&quot;>OpenStreetMap</a> contributors" url="https://tile.openstreetmap.org/{z}/{x}/{y}.png" maxZoom={19} />
      <FitAffectedAreas areas={drawable} />
      {affectedAreas.map(({ area, color, signalCount }) => <GeoJSONLayer key={area.id} data={area.geometry as GeoJSON.Geometry} style={{ color, weight: 2, fillColor: color, fillOpacity: .3 }} eventHandlers={{ click: () => onAreaSelect?.(area) }}><Popup><strong>{area.name}</strong><br />{signalCount} active signal{signalCount === 1 ? '' : 's'}<br />Click the polygon to prepare a case.</Popup></GeoJSONLayer>)}
    </MapContainer>
    <Typography variant="caption" sx={{ position: 'absolute', left: 8, top: 8, zIndex: 500, bgcolor: 'rgba(255,255,255,.92)', px: .75, py: .25, borderRadius: .5, pointerEvents: 'none' }}>Drag to pan · scroll or use controls to zoom · click an affected area.</Typography>
  </Box>
}
