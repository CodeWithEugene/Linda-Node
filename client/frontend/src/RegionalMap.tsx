import { useEffect, useRef, useState } from 'react'
import maplibregl, { Map as MapLibreMap, Popup } from 'maplibre-gl'
import Alert from '@mui/material/Alert'
import Box from '@mui/material/Box'
import Chip from '@mui/material/Chip'
import Stack from '@mui/material/Stack'
import Typography from '@mui/material/Typography'
import 'maplibre-gl/dist/maplibre-gl.css'
import type { RegionalUnit, TileSource } from './types'

const GHA_BOUNDS: [number, number, number, number] = [21.0, -12.5, 52.0, 23.0]
const STAGE_COLOR: Record<string, string> = { go: '#b71c1c', set: '#e65100', ready: '#f9a825' }
const NO_STAGE = '#9e9e9e'

/** Colour ramp for units that reach no stage, so the map still shows gradient. */
function probabilityColor(probability: number): string {
  if (probability >= 0.25) return '#c5b358'
  if (probability >= 0.15) return '#9fb08a'
  if (probability >= 0.05) return '#8fa7a0'
  return '#c8d3cc'
}

const LEGEND: [string, string][] = [
  ['GO', STAGE_COLOR.go],
  ['SET', STAGE_COLOR.set],
  ['READY', STAGE_COLOR.ready],
  ['No stage', NO_STAGE],
]

/**
 * Regional choropleth drawn straight from ICPAC's public pg_tileserv admin-1
 * layer. The tiles carry `gid_1`, the same GADM identifier the statistics
 * endpoint returns, so the join needs no intermediate geometry of our own.
 */
export function RegionalMap({ tiles, units, selectedCountry, onSelect, height = 380 }: {
  tiles: TileSource
  units: RegionalUnit[]
  selectedCountry?: string
  onSelect?: (areaId: string) => void
  height?: number
}) {
  const container = useRef<HTMLDivElement | null>(null)
  const map = useRef<MapLibreMap | null>(null)
  const [unsupported] = useState(() => {
    try {
      const probe = document.createElement('canvas')
      return !(probe.getContext('webgl2') || probe.getContext('webgl'))
    } catch {
      return true
    }
  })
  const [failed, setFailed] = useState<string | null>(null)

  useEffect(() => {
    if (unsupported || !container.current || map.current) return
    const instance = new maplibregl.Map({
      container: container.current,
      style: {
        version: 8,
        sources: {
          carto: {
            type: 'raster',
            tiles: ['https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png'],
            tileSize: 256,
            attribution: '© OpenStreetMap contributors © CARTO',
          },
          icpac: {
            type: 'vector',
            tiles: [tiles.tile_url],
            minzoom: tiles.min_zoom,
            maxzoom: tiles.max_zoom,
            attribution: tiles.attribution,
          },
        },
        layers: [
          { id: 'basemap', type: 'raster', source: 'carto' },
          {
            id: 'admin-fill',
            type: 'fill',
            source: 'icpac',
            'source-layer': tiles.source_layer,
            paint: { 'fill-color': NO_STAGE, 'fill-opacity': 0.55 },
          },
          {
            id: 'admin-outline',
            type: 'line',
            source: 'icpac',
            'source-layer': tiles.source_layer,
            paint: { 'line-color': '#37474f', 'line-width': 0.4, 'line-opacity': 0.6 },
          },
        ],
      },
      bounds: GHA_BOUNDS,
      fitBoundsOptions: { padding: 16 },
      attributionControl: { compact: true },
    })
    instance.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right')
    instance.on('error', (event) => {
      // Never swallow an error: a blank map with no explanation is worse than
      // a visible one. The ranking beside the map is unaffected either way.
      const message = String(event?.error?.message ?? event?.error ?? 'unknown map error')
      // eslint-disable-next-line no-console
      console.error('[RegionalMap]', message)
      setFailed(message)
    })
    instance.on('load', () => setFailed(null))
    map.current = instance
    return () => {
      instance.remove()
      map.current = null
    }
    // `tiles` is a stable descriptor from the API; the map is built once.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tiles.tile_url, tiles.source_layer, tiles.min_zoom, tiles.max_zoom])

  // Data-driven colour: one `match` expression keyed on the GADM id in the tile.
  useEffect(() => {
    const instance = map.current
    if (!instance) return
    const paint = () => {
      if (!instance.getLayer('admin-fill')) return
      const stops: (string | string[])[] = []
      for (const unit of units) {
        if (!unit.area_id) continue
        stops.push(unit.area_id, unit.stage ? STAGE_COLOR[unit.stage] : probabilityColor(unit.probability))
      }
      instance.setPaintProperty(
        'admin-fill',
        'fill-color',
        stops.length ? (['match', ['get', tiles.join_property], ...stops, '#e0e0e0'] as never) : '#e0e0e0',
      )
      instance.setPaintProperty(
        'admin-fill',
        'fill-opacity',
        selectedCountry
          ? (['case', ['==', ['slice', ['get', tiles.join_property], 0, 3], selectedCountry], 0.8, 0.2] as never)
          : 0.6,
      )
    }
    if (instance.isStyleLoaded()) paint()
    else instance.once('load', paint)
  }, [units, selectedCountry, tiles.join_property])

  // Hover and click on the same tile features.
  useEffect(() => {
    const instance = map.current
    if (!instance) return
    const byId = new Map(units.map((unit) => [unit.area_id, unit]))
    const popup = new Popup({ closeButton: false, closeOnClick: false, offset: 8 })

    const move = (event: maplibregl.MapLayerMouseEvent) => {
      const feature = event.features?.[0]
      const id = feature?.properties?.[tiles.join_property] as string | undefined
      const unit = id ? byId.get(id) : undefined
      instance.getCanvas().style.cursor = unit ? 'pointer' : ''
      if (!unit) {
        popup.remove()
        return
      }
      popup
        .setLngLat(event.lngLat)
        .setHTML(
          `<strong>${unit.area_name}</strong><br/>${unit.country_name}<br/>` +
            `${(unit.probability * 100).toFixed(1)}% rp3 exceedance<br/>` +
            (unit.stage ? `<strong>${unit.stage.toUpperCase()}</strong> · ${unit.ndma_phase}` : 'No activation recommended'),
        )
        .addTo(instance)
    }
    const leave = () => {
      instance.getCanvas().style.cursor = ''
      popup.remove()
    }
    const click = (event: maplibregl.MapLayerMouseEvent) => {
      const id = event.features?.[0]?.properties?.[tiles.join_property] as string | undefined
      if (id && byId.has(id)) onSelect?.(id)
    }

    instance.on('mousemove', 'admin-fill', move)
    instance.on('mouseleave', 'admin-fill', leave)
    instance.on('click', 'admin-fill', click)
    return () => {
      instance.off('mousemove', 'admin-fill', move)
      instance.off('mouseleave', 'admin-fill', leave)
      instance.off('click', 'admin-fill', click)
      popup.remove()
    }
  }, [units, onSelect, tiles.join_property])

  if (unsupported) {
    return (
      <Alert severity="info">
        This browser has WebGL disabled, so the map cannot render. Every unit is still listed and rankable beside it.
      </Alert>
    )
  }

  return (
    <Box>
      {failed && (
        <Alert severity="warning" sx={{ mb: 1 }}>
          The map could not draw ({failed.slice(0, 120)}). The ranking beside it is unaffected.
        </Alert>
      )}
      <Box
        ref={container}
        aria-label="Greater Horn of Africa readiness choropleth"
        sx={{ height, borderRadius: 1, overflow: 'hidden', border: 1, borderColor: 'divider' }}
      />
      <Stack direction="row" spacing={0.75} flexWrap="wrap" useFlexGap sx={{ mt: 1 }}>
        {LEGEND.map(([label, color]) => (
          <Chip
            key={label}
            size="small"
            variant="outlined"
            label={label}
            icon={<Box sx={{ width: 10, height: 10, borderRadius: '50%', bgcolor: color, ml: 1 }} />}
          />
        ))}
        <Typography variant="caption" color="text.secondary" sx={{ ml: 'auto' }}>
          Boundaries via ICPAC pg_tileserv · joined on {tiles.join_property}
        </Typography>
      </Stack>
    </Box>
  )
}
