import { lazy, ReactNode, Suspense, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import Alert from '@mui/material/Alert'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Card from '@mui/material/Card'
import CardContent from '@mui/material/CardContent'
import CardHeader from '@mui/material/CardHeader'
import Chip from '@mui/material/Chip'
import Dialog from '@mui/material/Dialog'
import DialogActions from '@mui/material/DialogActions'
import DialogContent from '@mui/material/DialogContent'
import DialogContentText from '@mui/material/DialogContentText'
import DialogTitle from '@mui/material/DialogTitle'
import Divider from '@mui/material/Divider'
import FormControl from '@mui/material/FormControl'
import Grid from '@mui/material/Grid2'
import InputLabel from '@mui/material/InputLabel'
import LinearProgress from '@mui/material/LinearProgress'
import MenuItem from '@mui/material/MenuItem'
import Paper from '@mui/material/Paper'
import Select from '@mui/material/Select'
import Skeleton from '@mui/material/Skeleton'
import Stack from '@mui/material/Stack'
import TextField from '@mui/material/TextField'
import ToggleButton from '@mui/material/ToggleButton'
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup'
import Tooltip from '@mui/material/Tooltip'
import Typography from '@mui/material/Typography'
import Public from '@mui/icons-material/Public'
import Refresh from '@mui/icons-material/Refresh'
import { api, post } from '../api'
import type { DecisionCase } from '../api'
const RegionalMap = lazy(() => import('../RegionalMap').then((module) => ({ default: module.RegionalMap })))
import { useSession } from '../session'
import {
  CopyButton,
  EmptyState,
  ErrorPanel,
  FreshnessBadge,
  HashBlock,
  meterColor,
  relativeTime,
  severityColor,
} from '../components'
import type { RegionalOverview, RegionalUnit } from '../types'

const STAGE_LABEL: Record<string, string> = { ready: 'READY', set: 'SET', go: 'GO' }

function StatTile({ label, value, caption, tone, active, onClick }: {
  label: string
  value: ReactNode
  caption: string
  tone?: 'error' | 'warning' | 'success' | 'info'
  active?: boolean
  onClick?: () => void
}) {
  return (
    <Paper
      variant="outlined"
      onClick={onClick}
      sx={{
        p: 2, height: '100%', cursor: onClick ? 'pointer' : 'default',
        borderColor: active ? 'primary.main' : 'divider',
        borderWidth: active ? 2 : 1,
        '&:hover': onClick ? { borderColor: 'primary.light' } : undefined,
      }}
    >
      <Typography variant="overline" color="text.secondary" display="block" noWrap>{label}</Typography>
      <Typography variant="h4" color={tone ? `${tone}.main` : 'text.primary'} sx={{ lineHeight: 1.1, my: 0.25 }}>{value}</Typography>
      <Typography variant="caption" color="text.secondary">{caption}</Typography>
    </Paper>
  )
}

function UnitRow({ unit, onOpen, canOpen, rank }: { unit: RegionalUnit; onOpen: () => void; canOpen: boolean; rank: number }) {
  return (
    <Paper
      variant="outlined"
      sx={{ p: 1.25, borderLeft: 4, borderLeftColor: unit.stage ? `${severityColor(unit.stage)}.main` : 'divider' }}
    >
      <Stack direction={{ xs: 'column', md: 'row' }} spacing={1.5} alignItems={{ md: 'center' }}>
        <Typography variant="caption" color="text.secondary" sx={{ width: 28 }}>#{rank}</Typography>
        <Box sx={{ minWidth: 0, flex: 1 }}>
          <Typography fontWeight={700} noWrap>{unit.area_name}</Typography>
          <Stack direction="row" spacing={0.75} alignItems="center" flexWrap="wrap" useFlexGap>
            <Chip size="small" variant="outlined" label={unit.country_name} />
            <Typography variant="caption" className="mono" color="text.secondary">{unit.area_id}</Typography>
            {unit.compound && <Chip size="small" color="warning" label="compound" />}
          </Stack>
        </Box>

        <Box sx={{ minWidth: 150 }}>
          <Stack direction="row" alignItems="baseline" spacing={0.5}>
            <Typography variant="h6" sx={{ lineHeight: 1 }}>{(unit.probability * 100).toFixed(1)}%</Typography>
            <Typography variant="caption" color="text.secondary">rp3 exceedance</Typography>
          </Stack>
          <LinearProgress
            variant="determinate"
            value={Math.min(100, unit.probability * 100)}
            color={meterColor(unit.stage ?? undefined)}
            sx={{ height: 6, borderRadius: 3, mt: 0.5 }}
          />
        </Box>

        <Box sx={{ minWidth: 170 }}>
          {unit.stage ? (
            <Stack spacing={0.25}>
              <Chip size="small" color={severityColor(unit.stage)} label={`${STAGE_LABEL[unit.stage]} · ${unit.ndma_phase}`} />
              <Typography variant="caption" color="text.secondary">via {unit.stage_hazard} policy</Typography>
            </Stack>
          ) : (
            <Typography variant="caption" color="text.secondary">no activation recommended</Typography>
          )}
        </Box>

        <Tooltip title={canOpen ? 'Open a governed decision case for this unit' : 'Requires County DRM Officer role'}>
          <span>
            <Button size="small" variant={unit.stage ? 'contained' : 'outlined'} disabled={!canOpen} onClick={onOpen}>
              Open case
            </Button>
          </span>
        </Tooltip>
      </Stack>
    </Paper>
  )
}

export function RegionalPage() {
  const { user } = useSession()
  const navigate = useNavigate()
  const client = useQueryClient()
  const [scope, setScope] = useState<'activating' | 'all'>('activating')
  const [country, setCountry] = useState('')
  const [pending, setPending] = useState<RegionalUnit | null>(null)
  const [title, setTitle] = useState('')

  const overview = useQuery({ queryKey: ['regional'], queryFn: () => api<RegionalOverview>('/api/regional') })
  const cases = useQuery({ queryKey: ['cases'], queryFn: () => api<{ id: string; area_id: string; hazard: string; state: string }[]>('/api/cases') })

  const refresh = useMutation({
    mutationFn: () => post<{ snapshot_ids: string[] }>('/api/sources/refresh'),
    onSuccess: () => {
      for (const key of ['regional', 'signals', 'sources-status']) client.invalidateQueries({ queryKey: [key] })
    },
  })
  const create = useMutation({
    mutationFn: async () => {
      const hazard = pending?.stage_hazard || 'drought'
      const created = await post<DecisionCase>('/api/cases', {
        area_id: pending!.area_id, area_name: pending!.area_name, hazard, title,
      })
      const sources = await api<{ sources: { id: string }[] }>('/api/sources/status')
      return post<DecisionCase>(`/api/cases/${created.id}/assess`, {
        snapshot_ids: sources.sources.map((item) => item.id),
        version: created.version,
      })
    },
    onSuccess: (assessed) => {
      client.invalidateQueries({ queryKey: ['cases'] })
      navigate(`/cases/${assessed.id}?tab=evidence`)
    },
  })

  const data = overview.data
  const caseByArea = useMemo(
    () => new Map((cases.data ?? []).map((item) => [item.area_id, item])),
    [cases.data],
  )
  const units = useMemo(() => {
    const all = data?.units ?? []
    return all.filter((unit) => (scope === 'all' || unit.stage) && (!country || unit.country === country))
  }, [data, scope, country])

  const openCase = (unit: RegionalUnit) => {
    const existing = caseByArea.get(unit.area_id)
    if (existing) {
      navigate(`/cases/${existing.id}`)
      return
    }
    setPending(unit)
    setTitle(`${data?.issue.season} ${data?.issue.year} ${unit.stage_hazard || 'drought'} — ${unit.area_name}, ${unit.country_name}`)
  }

  if (overview.isLoading) {
    return (
      <Stack spacing={2}>
        <Skeleton variant="rounded" height={90} />
        <Skeleton variant="rounded" height={120} />
        <Skeleton variant="rounded" height={480} />
      </Stack>
    )
  }
  if (overview.error) return <ErrorPanel error={overview.error} retry={() => overview.refetch()} />
  if (!data) return <EmptyState>No regional statistics are available.</EmptyState>

  const totals = data.totals
  const forecastEvidence = data.evidence.forecasts

  return (
    <Box>
      <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" alignItems={{ md: 'flex-start' }} spacing={2} mb={2}>
        <Box>
          <Stack direction="row" spacing={1} alignItems="center">
            <Public color="primary" />
            <Typography variant="h4">Regional readiness</Typography>
          </Stack>
          <Typography color="text.secondary">
            Every admin-1 unit ICPAC publishes statistics for, evaluated against the same versioned policy — {totals.units} units
            across {totals.countries} countries, from the {data.issue.season} {data.issue.year} {data.issue.indicator?.toUpperCase()} /{' '}
            {data.issue.data_source?.toUpperCase()} return-period forecast at {data.issue.lead_months}-month lead.
          </Typography>
        </Box>
        <Stack direction="row" spacing={1} alignItems="center">
          <FreshnessBadge value={forecastEvidence.freshness} retrievedAt={forecastEvidence.retrieved_at} />
          <Tooltip title="Fetch a new snapshot from every ICPAC source">
            <span>
              <Button startIcon={<Refresh />} variant="outlined" disabled={refresh.isPending} onClick={() => refresh.mutate()}>
                {refresh.isPending ? 'Refreshing…' : 'Refresh'}
              </Button>
            </span>
          </Tooltip>
        </Stack>
      </Stack>

      <Grid container spacing={2} sx={{ mb: 2 }}>
        <Grid size={{ xs: 6, md: 3 }}>
          <StatTile
            label="Units reaching a stage"
            value={totals.activating}
            caption={`of ${totals.units} assessed · ${totals.go} GO · ${totals.set} SET · ${totals.ready} READY`}
            tone={totals.activating ? 'error' : 'success'}
            active={scope === 'activating'}
            onClick={() => setScope(scope === 'activating' ? 'all' : 'activating')}
          />
        </Grid>
        <Grid size={{ xs: 6, md: 3 }}>
          <StatTile label="Highest exceedance" value={`${(totals.max_probability * 100).toFixed(1)}%`} caption={`${data.units[0]?.area_name}, ${data.units[0]?.country_name}`} />
        </Grid>
        <Grid size={{ xs: 6, md: 3 }}>
          <StatTile label="Countries covered" value={totals.countries} caption="Greater Horn of Africa admin-1" />
        </Grid>
        <Grid size={{ xs: 6, md: 3 }}>
          <StatTile label="Compound overlaps" value={totals.compound} caption="two hazard categories in one unit" tone={totals.compound ? 'warning' : undefined} />
        </Grid>
      </Grid>

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, lg: 7 }}>
          <Card>
            <CardHeader
              title="Readiness ranking"
              subheader="Ranked by stage reached, then by exceedance probability"
              titleTypographyProps={{ variant: 'subtitle1', fontWeight: 700 }}
            />
            <Divider />
            <Box sx={{ px: 2, py: 1.25, display: 'flex', gap: 1, alignItems: 'center', flexWrap: 'wrap' }}>
              <ToggleButtonGroup size="small" value={scope} exclusive onChange={(_, value) => value && setScope(value)}>
                <ToggleButton value="activating">Reaching a stage</ToggleButton>
                <ToggleButton value="all">All {totals.units}</ToggleButton>
              </ToggleButtonGroup>
              <FormControl size="small" sx={{ minWidth: 160 }}>
                <InputLabel>Country</InputLabel>
                <Select label="Country" value={country} onChange={(event) => setCountry(event.target.value)}>
                  <MenuItem value="">All countries</MenuItem>
                  {data.countries.map((item) => (
                    <MenuItem key={item.country} value={item.country}>
                      {item.country_name} ({item.activating}/{item.units})
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              <Box sx={{ flex: 1 }} />
              <Typography variant="caption" color="text.secondary">{units.length} shown</Typography>
            </Box>
            <Divider />
            <CardContent sx={{ maxHeight: 560, overflowY: 'auto' }}>
              {units.length === 0 ? (
                <EmptyState action={<Button size="small" onClick={() => { setScope('all'); setCountry('') }}>Show all units</Button>}>
                  No admin-1 unit currently reaches a policy stage
                  {country ? ` in ${data.countries.find((item) => item.country === country)?.country_name}` : ''}. That is the correct
                  result for this forecast issue, not an empty screen.
                </EmptyState>
              ) : (
                <Stack spacing={1}>
                  {units.map((unit, index) => (
                    <UnitRow
                      key={unit.area_id}
                      unit={unit}
                      rank={index + 1}
                      canOpen={user?.role === 'county_drm_officer'}
                      onOpen={() => openCase(unit)}
                    />
                  ))}
                </Stack>
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, lg: 5 }}>
          <Stack spacing={2}>
            <Card>
              <CardHeader
                title="Greater Horn of Africa"
                subheader="GADM admin-1 vector tiles served by ICPAC, shaded by exceedance"
                titleTypographyProps={{ variant: 'subtitle1', fontWeight: 700 }}
              />
              <CardContent sx={{ pt: 0 }}>
                <Suspense fallback={<Skeleton variant="rounded" height={380} />}>
                <RegionalMap
                  tiles={data.tiles}
                  units={data.units}
                  selectedCountry={country || undefined}
                  onSelect={(areaId) => {
                    const unit = data.units.find((item) => item.area_id === areaId)
                    if (unit) openCase(unit)
                  }}
                />
                </Suspense>
              </CardContent>
            </Card>

            <Card>
              <CardHeader title="Grounding evidence" subheader="Hashes cover the verbatim upstream bodies" titleTypographyProps={{ variant: 'subtitle1', fontWeight: 700 }} />
              <CardContent sx={{ pt: 0 }}>
                <Stack spacing={1}>
                  {Object.entries(data.evidence).map(([name, item]) => (
                    <Paper key={name} variant="outlined" sx={{ p: 1 }}>
                      <Stack direction="row" justifyContent="space-between" alignItems="center" spacing={1}>
                        <Typography variant="body2" fontWeight={600}>{name}</Typography>
                        <Stack direction="row" spacing={0.5} alignItems="center">
                          <FreshnessBadge value={item.freshness} retrievedAt={item.retrieved_at} />
                          <HashBlock value={item.sha256} />
                        </Stack>
                      </Stack>
                      <Stack direction="row" alignItems="center" spacing={0.25}>
                        <Typography variant="caption" className="mono" color="text.secondary" sx={{ wordBreak: 'break-all' }}>
                          {item.endpoint_url}
                        </Typography>
                        <CopyButton value={item.endpoint_url} label="Copy endpoint" />
                      </Stack>
                    </Paper>
                  ))}
                  <Typography variant="caption" color="text.secondary">
                    Policy versions — {Object.entries(data.policies).map(([hazard, id]) => `${hazard} ${id.slice(0, 8)}`).join(' · ')}
                  </Typography>
                </Stack>
              </CardContent>
            </Card>

            <Card>
              <CardHeader title="Country rollup" titleTypographyProps={{ variant: 'subtitle1', fontWeight: 700 }} />
              <CardContent sx={{ pt: 0, maxHeight: 300, overflowY: 'auto' }}>
                <Stack spacing={0.75}>
                  {data.countries.map((item) => (
                    <Stack
                      key={item.country}
                      direction="row"
                      alignItems="center"
                      spacing={1}
                      sx={{ cursor: 'pointer' }}
                      onClick={() => setCountry(country === item.country ? '' : item.country)}
                    >
                      <Typography variant="body2" sx={{ width: 110 }} noWrap>{item.country_name}</Typography>
                      <LinearProgress
                        variant="determinate"
                        value={Math.min(100, item.max_probability * 100)}
                        color={item.activating ? 'warning' : 'primary'}
                        sx={{ flex: 1, height: 6, borderRadius: 3 }}
                      />
                      <Typography variant="caption" color="text.secondary" sx={{ width: 84, textAlign: 'right' }}>
                        {item.activating}/{item.units} · {(item.max_probability * 100).toFixed(0)}%
                      </Typography>
                    </Stack>
                  ))}
                </Stack>
              </CardContent>
            </Card>
          </Stack>
        </Grid>
      </Grid>

      <Dialog open={Boolean(pending)} onClose={() => setPending(null)} fullWidth maxWidth="sm">
        <DialogTitle>Open a decision case</DialogTitle>
        <DialogContent>
          <DialogContentText sx={{ mb: 2 }}>
            The current source snapshots become immutable evidence for {pending?.area_name}, {pending?.country_name}, and the
            deterministic policy is evaluated against them immediately.
          </DialogContentText>
          <Stack spacing={1.5}>
            <TextField fullWidth label="Case title" value={title} onChange={(event) => setTitle(event.target.value)} />
            <Stack direction="row" spacing={1}>
              <Chip size="small" className="mono" label={pending?.area_id} />
              <Chip size="small" label={pending?.stage_hazard || 'drought'} />
              {pending?.stage && <Chip size="small" color={severityColor(pending.stage)} label={STAGE_LABEL[pending.stage]} />}
            </Stack>
            {create.error && <Alert severity="error">{create.error.message}</Alert>}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPending(null)}>Cancel</Button>
          <Button variant="contained" disabled={!title || create.isPending} onClick={() => create.mutate()}>
            {create.isPending ? 'Assessing…' : 'Create and assess'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
