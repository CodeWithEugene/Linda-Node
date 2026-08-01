import { ReactNode, useMemo, useState } from 'react'
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
import Grid from '@mui/material/Grid2'
import LinearProgress from '@mui/material/LinearProgress'
import Paper from '@mui/material/Paper'
import Skeleton from '@mui/material/Skeleton'
import Stack from '@mui/material/Stack'
import Tab from '@mui/material/Tab'
import Tabs from '@mui/material/Tabs'
import TextField from '@mui/material/TextField'
import ToggleButton from '@mui/material/ToggleButton'
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup'
import Tooltip from '@mui/material/Tooltip'
import Typography from '@mui/material/Typography'
import Bolt from '@mui/icons-material/Bolt'
import Description from '@mui/icons-material/Description'
import Refresh from '@mui/icons-material/Refresh'
import Schedule from '@mui/icons-material/Schedule'
import Thunderstorm from '@mui/icons-material/Thunderstorm'
import WaterDrop from '@mui/icons-material/WaterDrop'
import WbSunny from '@mui/icons-material/WbSunny'
import { api, post } from '../api'
import type { DecisionCase } from '../api'
import { AreaMap } from '../AreaMap'
import { useSession } from '../session'
import {
  CopyButton,
  EmptyState,
  ErrorPanel,
  FreshnessBadge,
  HashBlock,
  SnapshotDialog,
  meterColor,
  relativeTime,
  severityColor,
  severityRank,
} from '../components'
import type { Area, Signal, SignalKind, SignalsResponse, SourceSnapshot, SourceStatus } from '../types'

const REFRESH_ROLES = ['county_drm_officer', 'ews_specialist', 'admin']
const KIND_LABEL: Record<Exclude<SignalKind, 'all'>, string> = {
  rules: 'Trigger rules',
  events: 'Detected events',
  forecasts: 'Seasonal forecasts',
  pipeline: 'Pipeline files',
}

const hazardIcon = (hazard?: string) =>
  hazard === 'flood' ? <WaterDrop fontSize="small" /> : hazard === 'heat' ? <WbSunny fontSize="small" /> : <Thunderstorm fontSize="small" />

const reading = (signal: Signal) =>
  signal.probability !== undefined
    ? `${Math.round(signal.probability * 100)}%`
    : signal.value !== undefined && signal.value !== null
      ? `${Number(signal.value).toFixed(1)}${signal.threshold_value ? ` / ${signal.threshold_value}` : ''}`
      : 'Rule armed'

/** Signals that plausibly need a decision: moderate severity or a real probability. */
const needsAttention = (signal: Signal) => severityRank(signal.severity) >= 3 || (signal.probability ?? 0) >= 0.35

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
        transition: 'border-color .15s ease',
        '&:hover': onClick ? { borderColor: 'primary.light' } : undefined,
      }}
    >
      <Typography variant="overline" color="text.secondary" display="block" noWrap>{label}</Typography>
      <Typography variant="h4" color={tone ? `${tone}.main` : 'text.primary'} sx={{ lineHeight: 1.1, my: 0.25 }}>{value}</Typography>
      <Typography variant="caption" color="text.secondary">{caption}</Typography>
    </Paper>
  )
}

function SignalRow({ signal, snapshot, onInspect, onOpenCase, canOpenCase, existingCase }: {
  signal: Signal
  snapshot?: SourceSnapshot
  onInspect: () => void
  onOpenCase: () => void
  canOpenCase: boolean
  existingCase?: DecisionCase | { id: string; state: string }
}) {
  const probability = signal.probability
  return (
    <Paper
      variant="outlined"
      sx={{
        p: 1.5,
        borderLeft: 4,
        borderLeftColor: needsAttention(signal) ? `${severityColor(signal.severity)}.main` : 'divider',
      }}
    >
      <Stack direction={{ xs: 'column', md: 'row' }} spacing={1.5} alignItems={{ md: 'center' }}>
        <Box sx={{ minWidth: 0, flex: 1 }}>
          <Stack direction="row" spacing={0.75} alignItems="center" sx={{ color: 'text.secondary' }}>
            {hazardIcon(signal.hazard)}
            <Typography fontWeight={700} color="text.primary" noWrap title={signal.name}>{signal.name}</Typography>
          </Stack>
          <Stack direction="row" spacing={0.75} alignItems="center" flexWrap="wrap" useFlexGap sx={{ mt: 0.5 }}>
            <Chip size="small" variant="outlined" label={signal.area_name || signal.area_id} />
            <Typography variant="caption" className="mono" color="text.secondary">
              {signal.indicator_name || signal.indicator}
            </Typography>
            {signal.severity && <Chip size="small" color={severityColor(signal.severity)} label={signal.severity} />}
            <FreshnessBadge value={signal.freshness} retrievedAt={snapshot?.retrieved_at} />
          </Stack>
        </Box>

        <Box sx={{ minWidth: 140 }}>
          <Typography variant="h6" sx={{ lineHeight: 1 }}>{reading(signal)}</Typography>
          {probability !== undefined ? (
            <>
              <LinearProgress
                variant="determinate"
                value={Math.min(100, probability * 100)}
                color={meterColor(signal.severity)}
                sx={{ height: 6, borderRadius: 3, my: 0.5 }}
              />
              <Typography variant="caption" color="text.secondary">exceedance probability</Typography>
            </>
          ) : (
            <Typography variant="caption" color="text.secondary">
              {signal.threshold_value ? `threshold ${signal.threshold_value}` : 'no numeric reading'}
            </Typography>
          )}
        </Box>

        <Stack direction="row" spacing={0.5} alignItems="center">
          <Tooltip title={`Snapshot ${snapshot?.payload_sha256?.slice(0, 12) ?? ''}`}>
            <span>
              <Button size="small" onClick={onInspect} startIcon={<Description />}>Provenance</Button>
            </span>
          </Tooltip>
          {existingCase ? (
            <Button size="small" variant="outlined" onClick={onOpenCase}>Open case</Button>
          ) : (
            <Tooltip title={canOpenCase ? 'Create a decision case grounded in this evidence' : 'Requires County DRM Officer role'}>
              <span>
                <Button size="small" variant="contained" disabled={!canOpenCase} onClick={onOpenCase}>Create case</Button>
              </span>
            </Tooltip>
          )}
        </Stack>
      </Stack>
      {signal.probability_source && (
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.75 }}>
          Probability source: {signal.probability_source}
        </Typography>
      )}
    </Paper>
  )
}

/** The pitch anchor: ICPAC's own engine has exactly two action types. */
function UpstreamActionsCard({ signals }: { signals?: SignalsResponse }) {
  const types = Array.from(new Set((signals?.upstream_actions ?? []).map((item) => item.action_type))).sort()
  const lastCheck = signals?.check_logs?.[0]
  return (
    <Card>
      <CardHeader
        avatar={<Bolt color="primary" />}
        title="ICPAC trigger actions"
        subheader="Read live from /api/triggers/actions/"
        titleTypographyProps={{ variant: 'subtitle1', fontWeight: 700 }}
      />
      <CardContent sx={{ pt: 0 }}>
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mb: 1.5 }}>
          {types.length ? types.map((type) => <Chip key={type} size="small" className="mono" label={type} />) : <Chip size="small" label="none reported" />}
          <Chip size="small" color="primary" variant="outlined" label="governed activation — Linda" />
        </Stack>
        <Typography variant="body2" color="text.secondary">
          ICPAC&rsquo;s trigger engine currently dispatches {types.length || 'no'} action type{types.length === 1 ? '' : 's'}. Linda adds the
          third: a governed activation with evidence, multi-role approval, and an immutable record.
        </Typography>
        {lastCheck && (
          <Stack direction="row" spacing={0.75} alignItems="center" sx={{ mt: 1.5, color: 'text.secondary' }}>
            <Schedule fontSize="small" />
            <Typography variant="caption">
              Last upstream rule check {relativeTime(lastCheck.check_date)} · {lastCheck.total_rules_checked ?? 0} rules ·{' '}
              {lastCheck.triggers_detected ?? 0} triggered
            </Typography>
          </Stack>
        )}
      </CardContent>
    </Card>
  )
}

function SourceHealthRail({ status, onInspect, onRefresh, canRefresh, refreshing }: {
  status?: SourceStatus
  onInspect: (snapshot: SourceSnapshot) => void
  onRefresh: () => void
  canRefresh: boolean
  refreshing: boolean
}) {
  return (
    <Card>
      <CardHeader
        title="Source health"
        subheader="Every reading below opens its immutable snapshot"
        titleTypographyProps={{ variant: 'subtitle1', fontWeight: 700 }}
        action={
          <Tooltip title={canRefresh ? 'Fetch a new snapshot from each source' : 'Requires County DRM, EWS, or Admin role'}>
            <span>
              <Button size="small" startIcon={<Refresh />} disabled={!canRefresh || refreshing} onClick={onRefresh}>
                {refreshing ? 'Refreshing…' : 'Refresh'}
              </Button>
            </span>
          </Tooltip>
        }
      />
      <CardContent sx={{ pt: 0 }}>
        <Stack spacing={1}>
          {status?.sources.map((source) => (
            <Paper
              key={source.id}
              variant="outlined"
              sx={{ p: 1, display: 'flex', gap: 1, alignItems: 'center', justifyContent: 'space-between', cursor: 'pointer' }}
              onClick={() => onInspect(source)}
            >
              <Box sx={{ minWidth: 0 }}>
                <Typography variant="body2" fontWeight={600} noWrap>{source.adapter}</Typography>
                <Typography variant="caption" color="text.secondary" noWrap title={source.meta?.label}>
                  {source.meta?.label ?? source.endpoint_url}
                </Typography>
              </Box>
              <Stack alignItems="flex-end" spacing={0.25}>
                <FreshnessBadge value={source.freshness} retrievedAt={source.retrieved_at} />
                {!source.schema_ok && <Chip size="small" color="error" label="schema invalid" />}
                <HashBlock value={source.payload_sha256} />
              </Stack>
            </Paper>
          ))}
        </Stack>
      </CardContent>
    </Card>
  )
}

export function InboxPage() {
  const { user } = useSession()
  const navigate = useNavigate()
  const client = useQueryClient()
  const [kind, setKind] = useState<SignalKind>('all')
  const [attentionOnly, setAttentionOnly] = useState(false)
  const [areaFilter, setAreaFilter] = useState<string | null>(null)
  const [snapshot, setSnapshot] = useState<SourceSnapshot | null>(null)
  const [pending, setPending] = useState<Signal | null>(null)
  const [title, setTitle] = useState('')

  const signals = useQuery({ queryKey: ['signals'], queryFn: () => api<SignalsResponse>('/api/signals') })
  const status = useQuery({ queryKey: ['sources-status'], queryFn: () => api<SourceStatus>('/api/sources/status') })
  const areas = useQuery({ queryKey: ['areas', 'KEN', 1], queryFn: () => api<Area[]>('/api/areas?country=KEN&level=1') })
  const cases = useQuery({ queryKey: ['cases'], queryFn: () => api<{ id: string; area_id: string; hazard: string; state: string }[]>('/api/cases') })

  const refresh = useMutation({
    mutationFn: () => post<{ snapshot_ids: string[] }>('/api/sources/refresh'),
    onSuccess: () => {
      for (const key of ['signals', 'sources-status', 'areas']) client.invalidateQueries({ queryKey: [key] })
    },
  })

  const create = useMutation({
    mutationFn: async () => {
      const created = await post<DecisionCase>('/api/cases', {
        area_id: pending?.area_id || 'KEN.3_1',
        area_name: pending?.area_name || pending?.area_id || 'Bungoma',
        hazard: pending?.hazard || 'drought',
        title,
      })
      const sources = await api<SourceStatus>('/api/sources/status')
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

  const grouped = useMemo(() => {
    const data = signals.data
    if (!data) return [] as Signal[]
    const all = kind === 'all' ? [...data.rules, ...data.events, ...data.forecasts, ...data.pipeline] : data[kind]
    return [...all]
      .filter((item) => (!areaFilter || item.area_id === areaFilter) && (!attentionOnly || needsAttention(item)))
      .sort((a, b) => severityRank(b.severity) - severityRank(a.severity) || (b.probability ?? 0) - (a.probability ?? 0))
  }, [signals.data, kind, areaFilter, attentionOnly])

  const everySignal = useMemo(() => {
    const data = signals.data
    return data ? [...data.rules, ...data.events, ...data.forecasts, ...data.pipeline] : []
  }, [signals.data])

  const snapshotById = useMemo(
    () => new Map((status.data?.sources ?? []).map((item) => [item.id, item])),
    [status.data],
  )
  const caseByArea = useMemo(
    () => new Map((cases.data ?? []).map((item) => [`${item.area_id}:${item.hazard}`, item])),
    [cases.data],
  )

  const attention = everySignal.filter(needsAttention)
  const freshest = status.data?.sources.reduce<string | undefined>(
    (newest, item) => (!newest || item.retrieved_at > newest ? item.retrieved_at : newest),
    undefined,
  )
  const invalidSchemas = (status.data?.sources ?? []).filter((item) => !item.schema_ok)
  const isReplay = status.data?.mode === 'replay_only'

  const startCase = (signal: Signal) => {
    const existing = caseByArea.get(`${signal.area_id}:${signal.hazard || 'drought'}`)
    if (existing) {
      navigate(`/cases/${existing.id}`)
      return
    }
    setPending(signal)
    setTitle(`${signal.name} — ${signal.area_name || signal.area_id}`)
  }

  const inspect = (signalOrSnapshot: Signal | SourceSnapshot) =>
    api<SourceSnapshot>(
      `/api/sources/snapshots/${'snapshot_id' in signalOrSnapshot ? signalOrSnapshot.snapshot_id : signalOrSnapshot.id}`,
    ).then(setSnapshot)

  return (
    <Box>
      <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" alignItems={{ sm: 'flex-start' }} spacing={1} mb={2}>
        <Box>
          <Typography variant="h4">Signal Inbox</Typography>
          <Typography color="text.secondary">
            Upstream evidence retained verbatim with its source URL, retrieval time, schema result, and content hash before it can ground a decision.
          </Typography>
        </Box>
        <Chip
          color={isReplay ? 'info' : 'success'}
          label={isReplay ? `Replay only · escalation step ${status.data?.escalation_step ?? 0}` : 'Live first'}
        />
      </Stack>

      <Grid container spacing={2} sx={{ mb: 2 }}>
        <Grid size={{ xs: 6, md: 3 }}>
          <StatTile
            label="Needs a decision"
            value={attention.length}
            caption={`of ${everySignal.length} signals · click to filter`}
            tone={attention.length ? 'error' : undefined}
            active={attentionOnly}
            onClick={() => setAttentionOnly((value) => !value)}
          />
        </Grid>
        <Grid size={{ xs: 6, md: 3 }}>
          <StatTile
            label="Open cases"
            value={(cases.data ?? []).filter((item) => !['REVOKED', 'REJECTED', 'HANDED_OFF'].includes(item.state)).length}
            caption={`${(cases.data ?? []).length} total decision cases`}
            onClick={() => navigate('/cases')}
          />
        </Grid>
        <Grid size={{ xs: 6, md: 3 }}>
          <StatTile label="Newest evidence" value={relativeTime(freshest)} caption={`${status.data?.sources.length ?? 0} sources connected`} />
        </Grid>
        <Grid size={{ xs: 6, md: 3 }}>
          <StatTile
            label="Schema health"
            value={invalidSchemas.length ? `${invalidSchemas.length} failing` : 'All valid'}
            caption={invalidSchemas.length ? invalidSchemas.map((item) => item.adapter).join(', ') : 'every snapshot passed its source schema'}
            tone={invalidSchemas.length ? 'error' : 'success'}
          />
        </Grid>
      </Grid>

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, lg: 7 }}>
          <Card>
            <Tabs value={kind} onChange={(_, value: SignalKind) => setKind(value)} variant="scrollable" scrollButtons="auto">
              <Tab value="all" label={`All (${everySignal.length})`} />
              {(Object.keys(KIND_LABEL) as (keyof typeof KIND_LABEL)[]).map((key) => (
                <Tab key={key} value={key} label={`${KIND_LABEL[key]} (${signals.data?.[key]?.length ?? 0})`} />
              ))}
            </Tabs>
            <Divider />
            <Box sx={{ px: 2, py: 1.25, display: 'flex', gap: 1, alignItems: 'center', flexWrap: 'wrap' }}>
              <ToggleButtonGroup size="small" value={attentionOnly ? 'attention' : 'everything'} exclusive onChange={(_, value) => value && setAttentionOnly(value === 'attention')}>
                <ToggleButton value="everything">Everything</ToggleButton>
                <ToggleButton value="attention">Needs a decision</ToggleButton>
              </ToggleButtonGroup>
              {areaFilter && (
                <Chip size="small" label={`Area: ${areas.data?.find((item) => item.id === areaFilter)?.name ?? areaFilter}`} onDelete={() => setAreaFilter(null)} />
              )}
              <Box sx={{ flex: 1 }} />
              <Typography variant="caption" color="text.secondary">{grouped.length} shown</Typography>
            </Box>
            <Divider />
            <CardContent sx={{ maxHeight: 620, overflowY: 'auto' }}>
              {signals.isLoading ? (
                <Stack spacing={1}>{[0, 1, 2, 3].map((row) => <Skeleton key={row} variant="rounded" height={82} />)}</Stack>
              ) : signals.error ? (
                <ErrorPanel error={signals.error} retry={() => signals.refetch()} />
              ) : grouped.length === 0 ? (
                <EmptyState
                  action={
                    (attentionOnly || areaFilter) && (
                      <Button size="small" onClick={() => { setAttentionOnly(false); setAreaFilter(null) }}>Clear filters</Button>
                    )
                  }
                >
                  {attentionOnly
                    ? 'No signal currently meets the attention threshold. That is a valid result, not an empty screen.'
                    : 'No signals are present in the latest source snapshots.'}
                </EmptyState>
              ) : (
                <Stack spacing={1}>
                  {grouped.map((signal) => (
                    <SignalRow
                      key={`${signal.source_adapter}-${signal.id}`}
                      signal={signal}
                      snapshot={snapshotById.get(signal.snapshot_id)}
                      onInspect={() => inspect(signal)}
                      onOpenCase={() => startCase(signal)}
                      canOpenCase={user?.role === 'county_drm_officer'}
                      existingCase={caseByArea.get(`${signal.area_id}:${signal.hazard || 'drought'}`)}
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
                title="Affected areas"
                subheader="Severity overlay from the current signal set · click an area to filter"
                titleTypographyProps={{ variant: 'subtitle1', fontWeight: 700 }}
              />
              <CardContent sx={{ pt: 0 }}>
                {areas.isLoading ? (
                  <Skeleton variant="rounded" height={380} />
                ) : areas.error ? (
                  <ErrorPanel error={areas.error} retry={() => areas.refetch()} />
                ) : (
                  <AreaMap
                    areas={areas.data ?? []}
                    signals={everySignal}
                    height={380}
                    onAreaSelect={(area) => setAreaFilter((current) => (current === area.id ? null : area.id))}
                  />
                )}
              </CardContent>
            </Card>
            <UpstreamActionsCard signals={signals.data} />
            <SourceHealthRail
              status={status.data}
              onInspect={(item) => inspect(item)}
              onRefresh={() => refresh.mutate()}
              canRefresh={REFRESH_ROLES.includes(user?.role ?? '')}
              refreshing={refresh.isPending}
            />
            {refresh.error && <ErrorPanel error={refresh.error} />}
          </Stack>
        </Grid>
      </Grid>

      <SnapshotDialog snapshot={snapshot} onClose={() => setSnapshot(null)} />

      <Dialog open={Boolean(pending)} onClose={() => setPending(null)} fullWidth maxWidth="sm">
        <DialogTitle>Create and assess a decision case</DialogTitle>
        <DialogContent>
          <DialogContentText sx={{ mb: 2 }}>
            Every current source snapshot becomes immutable evidence, and the deterministic policy is evaluated immediately. The
            assessment may well conclude that no activation is recommended.
          </DialogContentText>
          <Stack spacing={1.5}>
            <TextField fullWidth label="Case title" value={title} onChange={(event) => setTitle(event.target.value)} />
            <Stack direction="row" spacing={1}>
              <Chip size="small" label={pending?.area_name || pending?.area_id} />
              <Chip size="small" label={pending?.hazard || 'drought'} />
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

export function SourcesPage() {
  const { user } = useSession()
  const client = useQueryClient()
  const [snapshot, setSnapshot] = useState<SourceSnapshot | null>(null)
  const status = useQuery({ queryKey: ['sources-status'], queryFn: () => api<SourceStatus>('/api/sources/status') })
  const refresh = useMutation({
    mutationFn: () => post<{ snapshot_ids: string[] }>('/api/sources/refresh'),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ['sources-status'] })
      client.invalidateQueries({ queryKey: ['signals'] })
    },
  })
  const canRefresh = REFRESH_ROLES.includes(user?.role ?? '')

  return (
    <Box>
      <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" spacing={1} mb={2}>
        <Box>
          <Typography variant="h4">Sources</Typography>
          <Typography color="text.secondary">
            Each upstream body is stored verbatim and hashed before parsing, then labelled live, cached, stale, or replay.
          </Typography>
        </Box>
        <Tooltip title={canRefresh ? 'Fetch a new snapshot from every source' : 'Your role cannot refresh sources'}>
          <span>
            <Button variant="contained" startIcon={<Refresh />} disabled={!canRefresh || refresh.isPending} onClick={() => refresh.mutate()}>
              {refresh.isPending ? 'Refreshing…' : 'Refresh sources'}
            </Button>
          </span>
        </Tooltip>
      </Stack>

      {status.isLoading ? (
        <Stack spacing={2}>{[0, 1, 2, 3].map((row) => <Skeleton key={row} variant="rounded" height={120} />)}</Stack>
      ) : status.error ? (
        <ErrorPanel error={status.error} retry={() => status.refetch()} />
      ) : (
        <Grid container spacing={2}>
          {status.data?.sources.map((source) => (
            <Grid key={source.id} size={{ xs: 12, md: 6 }}>
              <Card sx={{ height: '100%' }}>
                <CardHeader
                  title={source.adapter}
                  subheader={source.meta?.label}
                  action={<FreshnessBadge value={source.freshness} retrievedAt={source.retrieved_at} />}
                />
                <CardContent>
                  <Stack spacing={1}>
                    <Stack direction="row" alignItems="center" spacing={0.5}>
                      <Typography className="mono" variant="caption" sx={{ wordBreak: 'break-all' }}>{source.endpoint_url}</Typography>
                      <CopyButton value={source.endpoint_url} label="Copy endpoint" />
                    </Stack>
                    <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
                      <Chip size="small" color={source.schema_ok ? 'success' : 'error'} label={source.schema_ok ? 'Schema valid' : 'Schema invalid'} />
                      {source.meta?.synthetic && <Chip size="small" color="info" label="Synthetic" />}
                      <HashBlock value={source.payload_sha256} />
                    </Stack>
                    {source.meta?.schema_errors?.length ? (
                      <Alert severity="error">{source.meta.schema_errors.join('; ')}</Alert>
                    ) : null}
                    {source.meta?.last_error && <Alert severity="warning">Upstream error: {source.meta.last_error}</Alert>}
                    <Button
                      size="small"
                      onClick={() => api<SourceSnapshot>(`/api/sources/snapshots/${source.id}`).then(setSnapshot)}
                    >
                      Inspect provenance
                    </Button>
                  </Stack>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}
      <SnapshotDialog snapshot={snapshot} onClose={() => setSnapshot(null)} />
    </Box>
  )
}
