import { ComposableMap, Geographies, Geography, Marker, ZoomableGroup } from 'react-simple-maps'
import { useMemo, useState } from 'react'
import { Box, Button, Stack, Typography } from '@mui/material'
import worldAtlas from 'world-atlas/countries-110m.json'

type Area = { id: string; name: string; geometry: GeoJSON.Geometry; country?: string; level?: number }
type Signal = { area_id: string; severity?: string; name: string }
type MapPosition = { coordinates: [number, number]; zoom: number }

const kenyaCenter: [number, number] = [37.9, 0.2]
const viewportCenter: [number, number] = [0, 0]

const severityColor = (severity = '') => {
  const normalized = severity.toLowerCase()
  if (['severe', 'high', 'go'].includes(normalized)) return '#b71c1c'
  if (['moderate', 'set', 'watch'].includes(normalized)) return '#ed6c02'
  return '#1b5e20'
}

export const areaCentroid = (geometry: GeoJSON.Geometry): [number, number] | null => {
  const positions: GeoJSON.Position[] = geometry.type === 'Polygon'
    ? geometry.coordinates.flat(1)
    : geometry.type === 'MultiPolygon'
      ? geometry.coordinates.flat(2)
      : []
  if (!positions.length) return null
  const [longitude, latitude] = positions.reduce(([totalLongitude, totalLatitude], [lng, lat]) => [totalLongitude + lng, totalLatitude + lat], [0, 0])
  return [longitude / positions.length, latitude / positions.length]
}

export function AreaMap({ areas, signals, onAreaSelect }: { areas: Area[]; signals: Signal[]; onAreaSelect?: (area: Area) => void }) {
  const [position, setPosition] = useState<MapPosition>({ coordinates: viewportCenter, zoom: 5 })
  const [hoveredAreaId, setHoveredAreaId] = useState<string | null>(null)
  const affectedAreas = useMemo(() => areas.flatMap((area) => {
    const coordinates = areaCentroid(area.geometry)
    if (!coordinates) return []
    const areaSignals = signals.filter((signal) => signal.area_id === area.id)
    const topSeverity = areaSignals.map((signal) => signal.severity || '').sort((a, b) => severityColor(b).localeCompare(severityColor(a)))[0]
    return [{ area, coordinates, color: severityColor(topSeverity), signalCount: areaSignals.length }]
  }), [areas, signals])

  const resetView = () => setPosition({ coordinates: viewportCenter, zoom: 5 })
  return <Box sx={{ position: 'relative', height: 300, borderRadius: 1, overflow: 'hidden', bgcolor: '#e8f0ed', border: 1, borderColor: 'divider' }}>
    <ComposableMap aria-label="Interactive affected areas map" width={800} height={460} projection="geoMercator" projectionConfig={{ center: kenyaCenter, scale: 1450 }} style={{ width: '100%', height: '100%' }}>
      <ZoomableGroup center={position.coordinates} zoom={position.zoom} minZoom={3} maxZoom={12} onMoveEnd={({ coordinates, zoom }) => setPosition({ coordinates, zoom })}>
        <Geographies geography={worldAtlas}>
          {({ geographies }) => geographies.map((geography) => {
            const isKenya = geography.properties.name === 'Kenya'
            return <Geography key={geography.rsmKey} geography={geography} style={{ default: { fill: isKenya ? '#d4e7d6' : '#f7faf8', stroke: '#aebbb3', strokeWidth: .65, outline: 'none' }, hover: { fill: isKenya ? '#c2ddc7' : '#eef4f0', stroke: '#80958a', strokeWidth: .75, outline: 'none' }, pressed: { fill: '#bad7bf', outline: 'none' } }} />
          })}
        </Geographies>
        {affectedAreas.map(({ area, coordinates, color, signalCount }) => {
          const isHovered = hoveredAreaId === area.id
          return <Marker key={area.id} coordinates={coordinates} onMouseEnter={() => setHoveredAreaId(area.id)} onMouseLeave={() => setHoveredAreaId(null)} onClick={() => onAreaSelect?.(area)} style={{ default: { cursor: 'pointer', outline: 'none' }, hover: { cursor: 'pointer', outline: 'none' }, pressed: { cursor: 'pointer', outline: 'none' } }}>
            <circle r={isHovered ? 13 : 10} fill={color} fillOpacity={.18} stroke={color} strokeWidth={isHovered ? 3 : 2} />
            <circle r={4} fill={color} stroke="#fff" strokeWidth={1.5} />
            {(isHovered || signalCount > 0) && <g pointerEvents="none"><rect x={12} y={-22} width={Math.max(78, area.name.length * 7.3)} height={24} rx={4} fill="#13291c" opacity={.94} /><text x={18} y={-6} fill="#fff" fontSize="11" fontFamily="system-ui, sans-serif">{area.name} · {signalCount}</text></g>}
          </Marker>
        })}
      </ZoomableGroup>
    </ComposableMap>
    <Stack direction="row" spacing={1} sx={{ position: 'absolute', top: 8, right: 8 }}><Button size="small" variant="contained" color="inherit" onClick={() => setPosition((current) => ({ ...current, zoom: Math.min(current.zoom + 1, 12) }))}>+</Button><Button size="small" variant="contained" color="inherit" onClick={() => setPosition((current) => ({ ...current, zoom: Math.max(current.zoom - 1, 3) }))}>−</Button><Button size="small" variant="contained" color="inherit" onClick={resetView}>Reset</Button></Stack>
    <Typography variant="caption" sx={{ position: 'absolute', left: 8, bottom: 8, bgcolor: 'rgba(255,255,255,.92)', px: .75, py: .25, borderRadius: .5, pointerEvents: 'none' }}>Drag to pan · scroll or use controls to zoom · select an affected area.</Typography>
  </Box>
}
