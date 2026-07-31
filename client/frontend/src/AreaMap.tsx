import { useEffect, useRef, useState } from 'react'
import { GeoJSONSource, LngLatBounds, Map, MapLayerMouseEvent, NavigationControl } from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { Alert, Box, Typography } from '@mui/material'

type Area = { id: string; name: string; geometry: GeoJSON.Geometry; country?: string; level?: number }
type Signal = { area_id: string; severity?: string; name: string }

const severityColor = (severity = '') => {
  const normalized = severity.toLowerCase()
  if (['severe', 'high', 'go'].includes(normalized)) return '#b71c1c'
  if (['moderate', 'set', 'watch'].includes(normalized)) return '#ed6c02'
  return '#1b5e20'
}

export function AreaMap({ areas, signals, onAreaSelect }: { areas: Area[]; signals: Signal[]; onAreaSelect?: (area: Area) => void }) {
  const container = useRef<HTMLDivElement | null>(null)
  const map = useRef<Map | null>(null)
  const selectArea = useRef(onAreaSelect)
  const [tilesUnavailable, setTilesUnavailable] = useState(false)

  useEffect(() => { selectArea.current = onAreaSelect }, [onAreaSelect])

  useEffect(() => {
    if (!container.current || map.current) return
    const instance = new Map({
      container: container.current,
      center: [37.9, 0.2],
      zoom: 5.2,
      attributionControl: false,
      style: {
        version: 8,
        sources: { carto: { type: 'raster', tiles: ['https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png'], tileSize: 256, attribution: '© OpenStreetMap contributors © CARTO' } },
        layers: [{ id: 'carto', type: 'raster', source: 'carto' }],
      },
    })
    instance.addControl(new NavigationControl({ showCompass: false }), 'top-right')
    instance.on('error', () => setTilesUnavailable(true))
    instance.on('load', () => {
      instance.addSource('linda-areas', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } })
      instance.addLayer({ id: 'linda-area-fill', type: 'fill', source: 'linda-areas', paint: { 'fill-color': ['get', 'color'], 'fill-opacity': .35 } })
      instance.addLayer({ id: 'linda-area-outline', type: 'line', source: 'linda-areas', paint: { 'line-color': ['get', 'color'], 'line-width': 2 } })
      instance.on('mouseenter', 'linda-area-fill', () => { instance.getCanvas().style.cursor = 'pointer' })
      instance.on('mouseleave', 'linda-area-fill', () => { instance.getCanvas().style.cursor = '' })
      instance.on('click', 'linda-area-fill', (event: MapLayerMouseEvent) => {
        const feature = event.features?.[0]
        if (!feature) return
        const area = areas.find((item) => item.id === feature.properties?.id)
        if (area) selectArea.current?.(area)
      })
    })
    map.current = instance
    return () => { instance.remove(); map.current = null }
  }, [])

  useEffect(() => {
    const instance = map.current
    if (!instance?.isStyleLoaded()) return
    const source = instance.getSource('linda-areas') as GeoJSONSource | undefined
    if (!source) return
    const data: GeoJSON.FeatureCollection = {
      type: 'FeatureCollection',
      features: areas.map((area) => {
        const areaSignals = signals.filter((signal) => signal.area_id === area.id)
        const topSeverity = areaSignals.map((signal) => signal.severity || '').sort((a, b) => severityColor(b).localeCompare(severityColor(a)))[0]
        return { type: 'Feature', properties: { id: area.id, name: area.name, signal_count: areaSignals.length, color: severityColor(topSeverity) }, geometry: area.geometry }
      }),
    }
    source.setData(data)
    if (areas.length) {
      const bounds = new LngLatBounds()
      for (const area of areas) {
        const coordinates = area.geometry.type === 'Polygon' ? area.geometry.coordinates.flat(2) : area.geometry.type === 'MultiPolygon' ? area.geometry.coordinates.flat(3) : []
        for (let index = 0; index < coordinates.length; index += 2) bounds.extend([Number(coordinates[index]), Number(coordinates[index + 1])])
      }
      if (!bounds.isEmpty()) instance.fitBounds(bounds, { padding: 36, maxZoom: 8, duration: 0 })
    }
  }, [areas, signals])

  return <Box sx={{ position: 'relative', height: 300, borderRadius: 1, overflow: 'hidden', bgcolor: 'grey.100' }}><Box ref={container} aria-label="Signal areas map" sx={{ position: 'absolute', inset: 0 }} />{tilesUnavailable && <Alert severity="warning" sx={{ position: 'absolute', bottom: 8, left: 8, right: 8 }}>Basemap unavailable. Stored area boundaries remain visible.</Alert>}<Typography variant="caption" sx={{ position: 'absolute', left: 8, bottom: 8, bgcolor: 'rgba(255,255,255,.88)', px: .75, py: .25, borderRadius: .5 }}>Click an area to prepare a case.</Typography></Box>
}
