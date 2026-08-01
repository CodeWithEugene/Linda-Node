import { ReactNode, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import Accordion from '@mui/material/Accordion'
import AccordionDetails from '@mui/material/AccordionDetails'
import AccordionSummary from '@mui/material/AccordionSummary'
import Alert from '@mui/material/Alert'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Card from '@mui/material/Card'
import CardActions from '@mui/material/CardActions'
import CardContent from '@mui/material/CardContent'
import CardHeader from '@mui/material/CardHeader'
import Checkbox from '@mui/material/Checkbox'
import Chip from '@mui/material/Chip'
import Dialog from '@mui/material/Dialog'
import DialogActions from '@mui/material/DialogActions'
import DialogContent from '@mui/material/DialogContent'
import DialogContentText from '@mui/material/DialogContentText'
import DialogTitle from '@mui/material/DialogTitle'
import Divider from '@mui/material/Divider'
import FormControl from '@mui/material/FormControl'
import FormControlLabel from '@mui/material/FormControlLabel'
import Grid from '@mui/material/Grid2'
import InputLabel from '@mui/material/InputLabel'
import LinearProgress from '@mui/material/LinearProgress'
import List from '@mui/material/List'
import ListItem from '@mui/material/ListItem'
import ListItemText from '@mui/material/ListItemText'
import MenuItem from '@mui/material/MenuItem'
import Paper from '@mui/material/Paper'
import Select from '@mui/material/Select'
import Skeleton from '@mui/material/Skeleton'
import Stack from '@mui/material/Stack'
import Step from '@mui/material/Step'
import StepLabel from '@mui/material/StepLabel'
import Stepper from '@mui/material/Stepper'
import Tab from '@mui/material/Tab'
import Table from '@mui/material/Table'
import TableBody from '@mui/material/TableBody'
import TableCell from '@mui/material/TableCell'
import TableHead from '@mui/material/TableHead'
import TableRow from '@mui/material/TableRow'
import Tabs from '@mui/material/Tabs'
import TextField from '@mui/material/TextField'
import Tooltip from '@mui/material/Tooltip'
import Typography from '@mui/material/Typography'
import Add from '@mui/icons-material/Add'
import Api from '@mui/icons-material/Api'
import Cancel from '@mui/icons-material/Cancel'
import CheckCircle from '@mui/icons-material/CheckCircle'
import Download from '@mui/icons-material/Download'
import ExpandMore from '@mui/icons-material/ExpandMore'
import GppGood from '@mui/icons-material/GppGood'
import PlayArrow from '@mui/icons-material/PlayArrow'
import SmartToy from '@mui/icons-material/SmartToy'
import { DataGrid, GridColDef } from '@mui/x-data-grid'
import { Timeline, TimelineConnector, TimelineContent, TimelineDot, TimelineItem, TimelineOppositeContent, TimelineSeparator } from '@mui/lab'
import { api, post } from '../api'
import type { ActionCard, DecisionCase, ExportRecord, Role, Task } from '../api'
import { useSession } from '../session'
import {
  CopyButton,
  EmptyState,
  ErrorPanel,
  FreshnessBadge,
  HashBlock,
  ProvenanceLegend,
  RoleLabel,
  SnapshotDialog,
  StageChip,
  StateChip,
  money,
} from '../components'
import type { ApprovalVerification, BlockerSuggestion, ExplainerResult, MatcherResult, SourceSnapshot, SourceStatus } from '../types'

const SIGNER_ROLES: Role[] = ['ews_specialist', 'county_drm_officer', 'ngo_finance_lead']
const BLOCKER_CODES = [
  'LOGISTICS_TRANSPORT', 'LOGISTICS_STORAGE', 'FINANCE_UNAVAILABLE', 'FINANCE_DELAYED',
  'AUTHORITY_APPROVAL_MISSING', 'DATA_MISSING', 'SECURITY_ACCESS', 'STAFFING', 'MARKET_CONDITIONS', 'OTHER',
]
const ROLE_ATTESTATION: Record<string, string> = {
  ews_specialist: 'Attests that the evidence trace and threshold exceedance are understood.',
  county_drm_officer: 'Attests local readiness and county administrative authority.',
  ngo_finance_lead: 'Attests the documented readiness recommendation and financing posture.',
}

const useCase = (caseId?: string) =>
  useQuery({ queryKey: ['case', caseId], queryFn: () => api<DecisionCase>(`/api/cases/${caseId}`), enabled: Boolean(caseId) })

const useAssistStatus = () =>
  useQuery({ queryKey: ['assists'], queryFn: () => api<{ available: boolean }>('/api/assists/status') })

function AiPanel({ title, subtitle, children, action }: { title: string; subtitle: string; children?: ReactNode; action: ReactNode }) {
  return (
    <Card className="dashed-ai">
      <CardHeader avatar={<SmartToy color="primary" />} title={title} subheader={subtitle} titleTypographyProps={{ variant: 'subtitle1', fontWeight: 700 }} />
      {children ? <CardContent sx={{ pt: 0 }}>{children}</CardContent> : null}
      <CardActions>{action}</CardActions>
    </Card>
  )
}

// --------------------------------------------------------------------------

export function CasesPage() {
  const { user } = useSession()
  const navigate = useNavigate()
  const cases = useQuery({
    queryKey: ['cases'],
    queryFn: () => api<Pick<DecisionCase, 'id' | 'title' | 'area_name' | 'hazard' | 'state' | 'stage' | 'version' | 'updated_at'>[]>('/api/cases'),
  })
  const columns: GridColDef[] = [
    { field: 'title', headerName: 'Decision case', flex: 1, minWidth: 240 },
    { field: 'area_name', headerName: 'Area', width: 120 },
    { field: 'hazard', headerName: 'Hazard', width: 100 },
    { field: 'stage', headerName: 'Stage', width: 200, renderCell: ({ row }) => <StageChip stage={row.stage} /> },
    { field: 'state', headerName: 'State', width: 160, renderCell: ({ value }) => <StateChip state={String(value)} /> },
    { field: 'updated_at', headerName: 'Updated', width: 180 },
  ]
  return (
    <Box>
      <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" spacing={1} mb={2}>
        <Box>
          <Typography variant="h4">Decision Cases</Typography>
          <Typography color="text.secondary">A human-governed record from readiness through approval to handoff.</Typography>
        </Box>
        <Tooltip title={user?.role === 'county_drm_officer' ? 'Cases start from a signal in the inbox' : 'Requires County DRM Officer role'}>
          <span>
            <Button startIcon={<Add />} variant="contained" disabled={user?.role !== 'county_drm_officer'} onClick={() => navigate('/')}>
              Create from a signal
            </Button>
          </span>
        </Tooltip>
      </Stack>
      {cases.isLoading ? (
        <Skeleton variant="rounded" height={360} />
      ) : cases.error ? (
        <ErrorPanel error={cases.error} retry={() => cases.refetch()} />
      ) : !cases.data?.length ? (
        <EmptyState action={<Button onClick={() => navigate('/')}>Go to the Signal Inbox</Button>}>No decision cases yet.</EmptyState>
      ) : (
        <Paper sx={{ height: 460 }}>
          <DataGrid
            rows={cases.data}
            columns={columns}
            disableRowSelectionOnClick
            onRowClick={(params) => navigate(`/cases/${params.row.id}`)}
            sx={{ border: 0, '& .MuiDataGrid-row': { cursor: 'pointer' } }}
          />
        </Paper>
      )}
    </Box>
  )
}

export function CaseDetailPage() {
  const { caseId } = useParams()
  const [params, setParams] = useSearchParams()
  const tab = params.get('tab') || 'evidence'
  const query = useCase(caseId)

  if (query.isLoading) return <Stack spacing={1}><Skeleton variant="rounded" height={90} /><Skeleton variant="rounded" height={420} /></Stack>
  if (query.error) return <ErrorPanel error={query.error} retry={() => query.refetch()} />
  if (!query.data) return <EmptyState>Case not found.</EmptyState>

  const caseItem = query.data
  const noActivation = !caseItem.stage
  return (
    <Box>
      <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" alignItems={{ md: 'center' }} spacing={1} mb={1}>
        <Box>
          <Typography variant="h4">{caseItem.title}</Typography>
          <Typography color="text.secondary">
            {caseItem.area_name} · {caseItem.hazard} ·{' '}
            <Tooltip title="Optimistic concurrency version — every mutation must supply it"><span>v{caseItem.version}</span></Tooltip>
          </Typography>
        </Box>
        <Stack direction="row" spacing={1} alignItems="center">
          <StateChip state={caseItem.state} />
          <StageChip stage={caseItem.stage} ndmaPhase={caseItem.assessment?.ndma_phase} />
        </Stack>
      </Stack>

      <CaseStateStepper state={caseItem.state} />

      {noActivation && (
        <Alert severity="info" sx={{ mb: 2 }}>
          <strong>No activation recommended.</strong> No stage condition in the active policy was met by the attached evidence. Linda
          reports this rather than inferring a stage.
        </Alert>
      )}
      {caseItem.assessment?.synthetic_observation && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          <strong>Synthetic observation.</strong> The probability driving this assessment comes from a labelled demo fixture, not a
          recorded ICPAC statistic: <span className="mono">{caseItem.assessment.observed_signal?.source}</span>
        </Alert>
      )}
      {caseItem.assessment?.compound_signals?.length ? (
        <Alert severity="warning" sx={{ mb: 2 }}>
          <strong>Compound signals present:</strong> {caseItem.assessment.compound_signals.join(' + ')} in this admin area. This is a
          deterministic overlap check, not a new scientific index.
        </Alert>
      ) : null}

      <Tabs value={tab} onChange={(_, value) => setParams({ tab: value })} variant="scrollable" allowScrollButtonsMobile sx={{ mb: 2 }}>
        <Tab value="evidence" label="Evidence" />
        <Tab value="actions" label="Actions & Readiness" />
        <Tab value="approvals" label="Approvals" />
        <Tab value="handoffs" label="Handoffs & Exports" />
        <Tab value="log" label="Audit log" />
      </Tabs>

      {tab === 'evidence' && <EvidenceTab caseItem={caseItem} />}
      {tab === 'actions' && <ActionsTab caseItem={caseItem} />}
      {tab === 'approvals' && <ApprovalsTab caseItem={caseItem} />}
      {tab === 'handoffs' && (
        <Stack spacing={2}>
          <ExportsTab caseItem={caseItem} />
          <WebhookDeliveryStatus caseId={caseItem.id} />
        </Stack>
      )}
      {tab === 'log' && <CaseAudit caseId={caseItem.id} />}
    </Box>
  )
}

function CaseStateStepper({ state }: { state: string }) {
  const steps = ['INGESTED', 'ASSESSED', 'READY_FOR_REVIEW', 'APPROVED', 'HANDED_OFF']
  const terminal = ['REJECTED', 'REVOKED'].includes(state)
  const active = steps.indexOf(state)
  return (
    <Stepper activeStep={terminal ? steps.length : Math.max(0, active)} alternativeLabel sx={{ mb: 2, '& .MuiStepLabel-label': { fontSize: { xs: '.62rem', sm: '.75rem' } } }}>
      {steps.map((step) => (
        <Step key={step} completed={!terminal && active > steps.indexOf(step)}>
          <StepLabel error={terminal}>{terminal && step === 'HANDED_OFF' ? state.replaceAll('_', ' ') : step.replaceAll('_', ' ')}</StepLabel>
        </Step>
      ))}
    </Stepper>
  )
}

// --------------------------------------------------------------------------
// Tab 1 — evidence and the deterministic trace.
// --------------------------------------------------------------------------

const SOURCE_COLOR: Record<string, 'success' | 'warning' | 'info'> = {
  official_source: 'success',
  policy_assumption: 'warning',
  user_entered: 'info',
}

function EvidenceTab({ caseItem }: { caseItem: DecisionCase }) {
  const { user } = useSession()
  const client = useQueryClient()
  const [snapshot, setSnapshot] = useState<SourceSnapshot | null>(null)
  const [explanation, setExplanation] = useState<ExplainerResult | null>(null)
  const assists = useAssistStatus()
  const sources = useQuery({ queryKey: ['sources-status'], queryFn: () => api<SourceStatus>('/api/sources/status') })
  const refresh = () => client.invalidateQueries({ queryKey: ['case', caseItem.id] })

  const assess = useMutation({
    mutationFn: () =>
      post<DecisionCase>(`/api/cases/${caseItem.id}/assess`, {
        snapshot_ids: sources.data?.sources.map((item) => item.id) ?? [],
        version: caseItem.version,
      }),
    onSuccess: refresh,
  })
  const attach = useMutation({
    mutationFn: (snapshotId: string) =>
      post<DecisionCase>(`/api/cases/${caseItem.id}/evidence`, { snapshot_ids: [snapshotId], version: caseItem.version }),
    onSuccess: refresh,
  })
  const explain = useMutation({
    mutationFn: () => post<ExplainerResult>(`/api/cases/${caseItem.id}/assists/explainer`, {}),
    onSuccess: setExplanation,
  })

  const assessment = caseItem.assessment ?? {}
  const costLoss = (assessment.cost_loss ?? {}) as Record<string, unknown>
  const costSources = (costLoss.sources as { field: string; source: string; citation: string }[] | undefined) ?? []
  const canAssess = user?.role === 'county_drm_officer'

  return (
    <Stack spacing={2}>
      <ProvenanceLegend />

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, md: 7 }}>
          <Card sx={{ height: '100%' }}>
            <CardHeader title="Grounding evidence" subheader="Immutable source snapshots selected for this decision" />
            <CardContent sx={{ pt: 0 }}>
              {caseItem.evidence.length ? (
                <List dense>
                  {caseItem.evidence.map((item) => (
                    <ListItem
                      key={item.id}
                      disableGutters
                      secondaryAction={
                        <Button size="small" onClick={() => api<SourceSnapshot>(`/api/sources/snapshots/${item.id}`).then(setSnapshot)}>
                          Provenance
                        </Button>
                      }
                    >
                      <ListItemText
                        primary={item.label}
                        secondaryTypographyProps={{ component: 'div' }}
                        secondary={
                          <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
                            <Typography variant="caption" className="mono" sx={{ wordBreak: 'break-all' }}>{item.endpoint_url}</Typography>
                            <FreshnessBadge value={item.freshness} />
                            <HashBlock value={item.payload_sha256} />
                          </Stack>
                        }
                      />
                    </ListItem>
                  ))}
                </List>
              ) : (
                <EmptyState>No source evidence is attached to this case yet.</EmptyState>
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, md: 5 }}>
          <Card sx={{ height: '100%' }}>
            <CardHeader title="Policy gates" subheader="All gates must pass before a case can be sent for review" />
            <CardContent sx={{ pt: 0 }}>
              {assessment.gates?.length ? (
                <Stack spacing={1}>
                  {assessment.gates.map((gate) => (
                    <Stack key={gate.id} direction="row" spacing={1} alignItems="flex-start">
                      {gate.passed ? <CheckCircle color="success" fontSize="small" /> : <Cancel color="error" fontSize="small" />}
                      <Box>
                        <Typography variant="body2" fontWeight={600}>{gate.id.replaceAll('_', ' ')}</Typography>
                        <Typography variant="caption" color="text.secondary">{gate.detail}</Typography>
                      </Box>
                    </Stack>
                  ))}
                </Stack>
              ) : (
                <Alert severity="info">Assess this case against the current source snapshots.</Alert>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Card>
        <CardHeader title="Why this action" subheader="Deterministic policy evaluation — no AI touches these numbers" />
        <CardContent sx={{ pt: 0 }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Stage</TableCell>
                <TableCell>Condition</TableCell>
                <TableCell align="right">Observed</TableCell>
                <TableCell>Result</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {(assessment.stage_trace ?? []).map((row) => (
                <TableRow key={row.stage}>
                  <TableCell><strong>{row.stage.toUpperCase()}</strong></TableCell>
                  <TableCell className="mono">{row.condition}</TableCell>
                  <TableCell align="right" className="mono">{row.observed === null || row.observed === undefined ? '—' : row.observed}</TableCell>
                  <TableCell>{row.passed ? <Chip size="small" color="success" label="met" /> : <Chip size="small" label="not met" />}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>

          {costLoss.formula ? (
            <Paper variant="outlined" sx={{ p: 2, mt: 2 }}>
              <Typography variant="overline" color="text.secondary">Expected avoidable loss</Typography>
              {assessment.observed_signal?.synthetic && (
                <Alert severity="warning" sx={{ mb: 1 }}>This probability is a labelled synthetic demo value, not an official statistic.</Alert>
              )}
              <Typography className="mono" variant="body2" sx={{ my: 1 }}>{String(costLoss.formula)}</Typography>
              <Typography className="mono" variant="body2">
                {Number(costLoss.probability ?? 0).toFixed(2)} × {String(costLoss.exposed_households)} hh × ${String(costLoss.loss_per_household_usd)} ×
                eff {String(costLoss.effectiveness)} = {money(Number(costLoss.expected_avoidable_loss_usd ?? 0))}
              </Typography>
              <Typography className="mono" variant="body2">
                − readiness tranche {money(Number(costLoss.action_cost_usd ?? 0))} = net {money(Number(costLoss.net_expected_benefit_usd ?? 0))}{' '}
                (required margin {money(Number(costLoss.margin_usd ?? 0))})
              </Typography>
              <Divider sx={{ my: 1.5 }} />
              <Stack spacing={0.75}>
                {costSources.map((item) => (
                  <Stack key={item.field} direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
                    <Chip size="small" color={SOURCE_COLOR[item.source] ?? 'default'} label={item.source.replaceAll('_', ' ')} />
                    <Typography variant="caption" className="mono">{item.field}</Typography>
                    <Typography variant="caption" color="text.secondary">{item.citation}</Typography>
                  </Stack>
                ))}
              </Stack>
            </Paper>
          ) : null}
        </CardContent>
      </Card>

      <AiPanel
        title="AI evidence explanation"
        subtitle="Reads the trace above; it cannot alter policy, gates, or case state"
        action={
          <Tooltip title={assists.data?.available ? 'Explain the existing evidence trace' : 'Gemini is not configured — the deterministic workflow is unaffected'}>
            <span>
              <Button startIcon={<SmartToy />} disabled={!assists.data?.available || explain.isPending || !caseItem.evidence.length} onClick={() => explain.mutate()}>
                {explain.isPending ? 'Running…' : 'Run explainer'}
              </Button>
            </span>
          </Tooltip>
        }
      >
        {explanation ? (
          <Stack spacing={1}>
            <Typography>{explanation.summary}</Typography>
            <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
              {explanation.cited_snapshot_ids.map((id) => <Chip key={id} size="small" className="mono" label={id.slice(0, 14)} />)}
            </Stack>
            {explanation.missing_inputs.length > 0 && (
              <Alert severity="warning">Missing inputs the assist refused to infer: {explanation.missing_inputs.join(', ')}</Alert>
            )}
          </Stack>
        ) : (
          <Typography variant="body2" color="text.secondary">No explanation generated yet.</Typography>
        )}
        {explain.error && <Alert severity="warning" sx={{ mt: 1 }}>{explain.error.message}</Alert>}
      </AiPanel>

      <Card>
        <CardHeader title="Attach evidence and re-assess" subheader="Re-assessment supersedes existing signatures while preserving the audit record" />
        <CardContent sx={{ pt: 0 }}>
          {sources.isLoading ? (
            <LinearProgress />
          ) : (
            <Stack spacing={1}>
              {sources.data?.sources.map((item) => (
                <Paper key={item.id} variant="outlined" sx={{ p: 1, display: 'flex', gap: 1, alignItems: 'center', justifyContent: 'space-between' }}>
                  <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
                    <Typography variant="body2" fontWeight={600}>{item.adapter}</Typography>
                    <FreshnessBadge value={item.freshness} retrievedAt={item.retrieved_at} />
                    <HashBlock value={item.payload_sha256} />
                  </Stack>
                  <Tooltip title={['county_drm_officer', 'ews_specialist'].includes(user?.role ?? '') ? 'Attach and re-assess' : 'Requires County DRM or EWS role'}>
                    <span>
                      <Button size="small" disabled={!['county_drm_officer', 'ews_specialist'].includes(user?.role ?? '') || attach.isPending} onClick={() => attach.mutate(item.id)}>
                        Attach
                      </Button>
                    </span>
                  </Tooltip>
                </Paper>
              ))}
            </Stack>
          )}
          {(assess.error || attach.error) && <ErrorPanel error={assess.error || attach.error} />}
        </CardContent>
        <CardActions>
          <Tooltip title={canAssess ? 'Evaluate the complete current source set' : 'Requires County DRM Officer role'}>
            <span>
              <Button variant="contained" disabled={!canAssess || !sources.data?.sources.length || assess.isPending} onClick={() => assess.mutate()}>
                {assess.isPending ? 'Assessing…' : caseItem.state === 'INGESTED' ? 'Assess case' : 'Re-assess case'}
              </Button>
            </span>
          </Tooltip>
        </CardActions>
      </Card>

      <SnapshotDialog snapshot={snapshot} onClose={() => setSnapshot(null)} />
    </Stack>
  )
}

// --------------------------------------------------------------------------
// Tab 2 — action cards and the readiness board.
// --------------------------------------------------------------------------

function ActionCardTile({ card, ineligibleReason }: { card: ActionCard; ineligibleReason?: string }) {
  return (
    <Card variant="outlined" sx={{ height: '100%', opacity: ineligibleReason ? 0.66 : 1 }}>
      <CardHeader
        title={card.title}
        subheader={<><RoleLabel role={card.owner_role} /> · {card.lead_time_days} days lead time</>}
        action={<Chip size="small" color={ineligibleReason ? 'default' : 'warning'} label={card.stage_required.toUpperCase()} />}
      />
      <CardContent sx={{ pt: 0 }}>
        <Typography variant="body2" sx={{ minHeight: 40 }}>{card.description}</Typography>
        <Divider sx={{ my: 1.5 }} />
        <Typography variant="body2"><strong>Readiness tranche:</strong> {money(card.budget.readiness_tranche.amount, card.budget.currency)} · at {card.budget.readiness_tranche.released_at_stage.toUpperCase()}</Typography>
        <Typography variant="body2"><strong>Action tranche:</strong> {money(card.budget.action_tranche.amount, card.budget.currency)} · at {card.budget.action_tranche.released_at_stage.toUpperCase()}</Typography>
        <Typography variant="caption" color="text.secondary">Recorded recommendation only — Linda Protocol moves no funds.</Typography>
        {ineligibleReason && <Alert severity="error" sx={{ mt: 1 }}>Ineligible: {ineligibleReason}</Alert>}
      </CardContent>
    </Card>
  )
}

function ActionsTab({ caseItem }: { caseItem: DecisionCase }) {
  const { user } = useSession()
  const client = useQueryClient()
  const [task, setTask] = useState<Task | null>(null)
  const [action, setAction] = useState('acknowledge')
  const [note, setNote] = useState('')
  const [code, setCode] = useState('LOGISTICS_TRANSPORT')
  const [matcher, setMatcher] = useState<MatcherResult | null>(null)
  const assists = useAssistStatus()
  const refresh = () => client.invalidateQueries({ queryKey: ['case', caseItem.id] })

  const taskMutation = useMutation({
    mutationFn: () =>
      post<DecisionCase>(`/api/cases/${caseItem.id}/tasks/${task!.id}`, {
        action,
        version: caseItem.version,
        blocker_code: ['block', 'decline'].includes(action) ? code : undefined,
        note: ['block', 'decline'].includes(action) ? note : undefined,
      }),
    onSuccess: () => { setTask(null); refresh() },
  })
  const matcherMutation = useMutation({
    mutationFn: () => post<MatcherResult>(`/api/cases/${caseItem.id}/assists/matcher`, {}),
    onSuccess: setMatcher,
  })
  const review = useMutation({
    mutationFn: () => post<DecisionCase>(`/api/cases/${caseItem.id}/transition`, { to_state: 'READY_FOR_REVIEW', version: caseItem.version }),
    onSuccess: refresh,
  })

  const ineligible = useMemo(
    () => new Map((caseItem.assessment?.ineligible ?? []).map((item) => [item.card, item.reason])),
    [caseItem.assessment],
  )
  const rows = useMemo(
    () => caseItem.tasks.map((item) => ({ ...item, owner: item.owner_role.replaceAll('_', ' '), blocker: item.blocker_code ? `${item.blocker_code}: ${item.blocker_note ?? ''}` : '—' })),
    [caseItem.tasks],
  )
  const blocking = caseItem.tasks.filter((item) => item.criticality === 'critical' && !['ACKNOWLEDGED', 'RESOLVED'].includes(item.state))
  const failedGates = (caseItem.assessment?.gates ?? []).filter((gate) => !gate.passed)

  const columns: GridColDef[] = [
    { field: 'title', headerName: 'Task', minWidth: 230, flex: 1 },
    { field: 'action_card_id', headerName: 'Action card', minWidth: 180 },
    { field: 'owner', headerName: 'Owner role', minWidth: 150 },
    { field: 'criticality', headerName: 'Criticality', width: 110, renderCell: ({ value }) => <Chip size="small" color={value === 'critical' ? 'error' : 'default'} label={String(value)} /> },
    { field: 'state', headerName: 'State', width: 140, renderCell: ({ value }) => <StateChip state={String(value)} /> },
    { field: 'blocker', headerName: 'Blocker', minWidth: 240, flex: 1 },
    {
      field: 'update', headerName: '', width: 120, sortable: false,
      renderCell: (params) => (
        <Tooltip title={user?.role === params.row.owner_role ? 'Update this assigned task' : 'Only the assigned owner role can update it'}>
          <span>
            <Button
              size="small"
              disabled={user?.role !== params.row.owner_role || ['REJECTED', 'REVOKED'].includes(caseItem.state)}
              onClick={() => {
                setTask(params.row)
                setAction(params.row.state === 'BLOCKED' ? 'resolve' : 'acknowledge')
                setCode(params.row.blocker_code || 'LOGISTICS_TRANSPORT')
                setNote(params.row.blocker_note || '')
              }}
            >
              Update
            </Button>
          </span>
        </Tooltip>
      ),
    },
  ]

  return (
    <Stack spacing={2}>
      <ProvenanceLegend />
      <Grid container spacing={2}>
        {caseItem.action_cards.map((card) => (
          <Grid key={card.id} size={{ xs: 12, md: 6 }}>
            <ActionCardTile card={card} ineligibleReason={ineligible.get(card.id)} />
          </Grid>
        ))}
      </Grid>

      <AiPanel
        title="AI action matcher"
        subtitle="Ranks only cards already eligible under deterministic policy; it cannot add cards or change gates"
        action={
          <Tooltip title={assists.data?.available ? 'Run the constrained matcher' : 'Gemini is not configured — the deterministic workflow is unaffected'}>
            <span>
              <Button startIcon={<PlayArrow />} disabled={!assists.data?.available || matcherMutation.isPending} onClick={() => matcherMutation.mutate()}>
                {matcherMutation.isPending ? 'Ranking…' : 'Run matcher'}
              </Button>
            </span>
          </Tooltip>
        }
      >
        {matcher ? (
          <List dense>
            {matcher.candidates.map((candidate) => (
              <ListItem key={candidate.card_id} disableGutters>
                <ListItemText primary={`#${candidate.rank} · ${candidate.card_id}`} secondary={candidate.rationale} />
              </ListItem>
            ))}
          </List>
        ) : (
          <Typography variant="body2" color="text.secondary">No ranking generated yet.</Typography>
        )}
        {matcherMutation.error && <Alert severity="warning" sx={{ mt: 1 }}>{matcherMutation.error.message}</Alert>}
      </AiPanel>

      <Paper sx={{ height: 440 }}>
        <DataGrid rows={rows} columns={columns} disableRowSelectionOnClick sx={{ border: 0 }} />
      </Paper>

      <Paper sx={{ p: 2, position: 'sticky', bottom: 12, border: 1, borderColor: blocking.length || failedGates.length ? 'error.main' : 'success.main' }}>
        <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" alignItems={{ sm: 'center' }} spacing={1}>
          {blocking.length || failedGates.length ? (
            <Alert severity="error" sx={{ flex: 1 }}>
              {blocking.length ? `Blocked: ${blocking.map((item) => `'${item.title}' is ${item.state}`).join(', ')}. ` : ''}
              {failedGates.length ? `Failed gates: ${failedGates.map((gate) => gate.id).join(', ')}.` : ''}
            </Alert>
          ) : (
            <Alert severity="success" sx={{ flex: 1 }}>All gates passed and every critical readiness task is acknowledged or resolved.</Alert>
          )}
          <Tooltip title={user?.role === 'county_drm_officer' ? 'Send this case for multi-role review' : 'Requires County DRM Officer role'}>
            <span>
              <Button
                variant="contained"
                disabled={Boolean(blocking.length || failedGates.length) || user?.role !== 'county_drm_officer' || caseItem.state !== 'ASSESSED' || review.isPending}
                onClick={() => review.mutate()}
              >
                {review.isPending ? 'Sending…' : 'Send for review'}
              </Button>
            </span>
          </Tooltip>
        </Stack>
        {review.error && <ErrorPanel error={review.error} />}
      </Paper>

      <TaskDialog
        task={task}
        action={action}
        setAction={setAction}
        code={code}
        setCode={setCode}
        note={note}
        setNote={setNote}
        onClose={() => setTask(null)}
        onSubmit={() => taskMutation.mutate()}
        busy={taskMutation.isPending}
        error={taskMutation.error}
        caseId={caseItem.id}
        assistsEnabled={Boolean(assists.data?.available)}
      />
    </Stack>
  )
}

function TaskDialog(props: {
  task: Task | null
  action: string
  setAction: (value: string) => void
  code: string
  setCode: (value: string) => void
  note: string
  setNote: (value: string) => void
  onClose: () => void
  onSubmit: () => void
  busy: boolean
  error: Error | null
  caseId: string
  assistsEnabled: boolean
}) {
  const { task, action, setAction, code, setCode, note, setNote, onClose, onSubmit, busy, error, caseId, assistsEnabled } = props
  const [suggestion, setSuggestion] = useState<BlockerSuggestion | null>(null)
  const classify = useMutation({
    mutationFn: () => post<BlockerSuggestion>(`/api/cases/${caseId}/assists/blockers`, { report: note }),
    onSuccess: (result) => { setSuggestion(result); setCode(result.code) },
  })
  const needsBlocker = ['block', 'decline'].includes(action)

  return (
    <Dialog open={Boolean(task)} onClose={onClose} fullWidth maxWidth="sm">
      <DialogTitle>Update readiness task</DialogTitle>
      <DialogContent>
        <DialogContentText sx={{ mb: 2 }}>{task?.title}</DialogContentText>
        <Stack spacing={2}>
          <FormControl fullWidth>
            <InputLabel>Action</InputLabel>
            <Select label="Action" value={action} onChange={(event) => setAction(event.target.value)}>
              <MenuItem value="acknowledge">Acknowledge</MenuItem>
              <MenuItem value="resolve">Resolve</MenuItem>
              <MenuItem value="block">Report blocker</MenuItem>
              <MenuItem value="decline">Decline</MenuItem>
            </Select>
          </FormControl>
          {needsBlocker && (
            <>
              <FormControl fullWidth>
                <InputLabel>Blocker code</InputLabel>
                <Select label="Blocker code" value={code} onChange={(event) => setCode(event.target.value)}>
                  {BLOCKER_CODES.map((item) => <MenuItem key={item} value={item}>{item}</MenuItem>)}
                </Select>
              </FormControl>
              <TextField
                multiline
                minRows={3}
                label="What is blocking readiness?"
                value={note}
                onChange={(event) => setNote(event.target.value)}
                helperText="A taxonomy code and an explanatory note are both required."
              />
              <Tooltip title={assistsEnabled ? 'Suggest a taxonomy code — a human must confirm it' : 'Gemini is not configured'}>
                <span>
                  <Button startIcon={<SmartToy />} disabled={!assistsEnabled || !note || classify.isPending} onClick={() => classify.mutate()}>
                    Suggest classification
                  </Button>
                </span>
              </Tooltip>
              {suggestion && (
                <Alert severity="info">
                  Suggested {suggestion.code} ({suggestion.severity}): {suggestion.summary} Human confirmation is still required.
                </Alert>
              )}
              {classify.error && <Alert severity="warning">{classify.error.message}</Alert>}
            </>
          )}
          {error && <Alert severity="error">{error.message}</Alert>}
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button variant="contained" disabled={busy || (needsBlocker && !note.trim())} onClick={onSubmit}>
          {busy ? 'Saving…' : 'Save update'}
        </Button>
      </DialogActions>
    </Dialog>
  )
}

// --------------------------------------------------------------------------
// Tab 3 — approvals.
// --------------------------------------------------------------------------

function ApprovalsTab({ caseItem }: { caseItem: DecisionCase }) {
  const { user } = useSession()
  const client = useQueryClient()
  const [decision, setDecision] = useState<string | null>(null)
  const [comment, setComment] = useState('')
  const [reviewed, setReviewed] = useState(false)

  const verification = useQuery({
    queryKey: ['approval-verification', caseItem.id, caseItem.version],
    queryFn: () => api<ApprovalVerification>(`/api/cases/${caseItem.id}/approvals/verify`),
  })
  const mutation = useMutation({
    mutationFn: () => post<DecisionCase>(`/api/cases/${caseItem.id}/approvals`, { decision, comment: comment || undefined, version: caseItem.version }),
    onSuccess: () => {
      setDecision(null); setComment(''); setReviewed(false)
      client.invalidateQueries({ queryKey: ['case', caseItem.id] })
      client.invalidateQueries({ queryKey: ['approval-verification', caseItem.id] })
    },
  })

  const live = (role: Role) => caseItem.approvals.find((item) => item.role === role && !item.superseded)
  const approved = caseItem.approvals.filter((item) => !item.superseded && item.decision === 'approve').length

  return (
    <Stack spacing={2}>
      <Alert severity="info">
        Three distinct roles must sign the same canonical case digest. This is HMAC-SHA256 integrity protection and non-repudiation
        <em> within this demo system</em> using server-held keys — not PKI, not a blockchain. {approved} of 3 recorded.
      </Alert>

      <Grid container spacing={2}>
        {SIGNER_ROLES.map((role) => {
          const approval = live(role)
          const own = user?.role === role
          return (
            <Grid key={role} size={{ xs: 12, md: 4 }}>
              <Card sx={{ height: '100%' }}>
                <CardHeader title={<RoleLabel role={role} />} subheader={ROLE_ATTESTATION[role]} />
                <CardContent sx={{ pt: 0 }}>
                  {approval ? (
                    <Stack spacing={1}>
                      <StateChip state={approval.decision === 'approve' ? 'APPROVED' : approval.decision.toUpperCase()} />
                      <Typography variant="body2">{approval.display_name} · {approval.org}</Typography>
                      <Typography variant="caption" color="text.secondary">{approval.signed_at}</Typography>
                      <HashBlock value={approval.signature} label="Signature" />
                    </Stack>
                  ) : (
                    <Chip size="small" label="Awaiting decision" />
                  )}
                </CardContent>
                {own && caseItem.state === 'READY_FOR_REVIEW' && !approval && (
                  <CardActions>
                    <Button color="success" onClick={() => setDecision('approve')}>Approve &amp; sign</Button>
                    <Button onClick={() => setDecision('request_evidence')}>Request evidence</Button>
                    <Button color="error" onClick={() => setDecision('reject')}>Reject</Button>
                  </CardActions>
                )}
              </Card>
            </Grid>
          )
        })}
      </Grid>

      {caseItem.approvals.some((item) => item.superseded) && (
        <Alert severity="warning">Evidence was re-assessed after signing. Superseded signatures are retained but must be collected again.</Alert>
      )}

      <Accordion defaultExpanded>
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Stack direction="row" spacing={1} alignItems="center">
            <GppGood color="success" />
            <Typography>Verify signatures</Typography>
          </Stack>
        </AccordionSummary>
        <AccordionDetails>
          {verification.isLoading ? (
            <LinearProgress />
          ) : verification.error ? (
            <ErrorPanel error={verification.error} retry={() => verification.refetch()} />
          ) : (
            <Stack spacing={1}>
              <Stack direction="row" spacing={0.5} alignItems="center">
                <Typography variant="body2">Current digest:</Typography>
                <Typography className="mono" variant="body2" sx={{ wordBreak: 'break-all' }}>{verification.data?.current_digest}</Typography>
                <CopyButton value={verification.data?.current_digest ?? ''} label="Copy digest" />
              </Stack>
              {verification.data?.signatures.map((signature) => (
                <Alert key={`${signature.role}-${signature.signed_at}`} severity={signature.signature_valid && signature.covers_current_case ? 'success' : 'warning'}>
                  <strong>{signature.role.replaceAll('_', ' ')}</strong> · {signature.signature_valid ? 'valid HMAC' : 'invalid HMAC'} ·{' '}
                  {signature.covers_current_case ? 'covers the current case' : 'does not cover the current case'} · {signature.signer}
                </Alert>
              ))}
              <Alert severity={verification.data?.three_role_approval_valid ? 'success' : 'info'}>
                {verification.data?.three_role_approval_valid
                  ? 'All three role approvals are valid and cover the same case digest.'
                  : 'Three valid role approvals covering the current digest are not yet present.'}
              </Alert>
            </Stack>
          )}
        </AccordionDetails>
      </Accordion>

      <Dialog open={Boolean(decision)} onClose={() => setDecision(null)} fullWidth maxWidth="sm">
        <DialogTitle>
          {decision === 'approve' ? 'Approve and sign the decision record' : decision === 'reject' ? 'Reject this decision case' : 'Request more evidence'}
        </DialogTitle>
        <DialogContent>
          <DialogContentText sx={{ mb: 2 }}>
            Your signature covers the assessment, {caseItem.tasks.length} readiness tasks, and {caseItem.evidence.length} evidence snapshots.
          </DialogContentText>
          {verification.data && (
            <Paper variant="outlined" sx={{ p: 1, mb: 2 }}>
              <Typography variant="caption" className="mono" sx={{ wordBreak: 'break-all' }}>{verification.data.current_digest}</Typography>
            </Paper>
          )}
          {decision === 'approve' && (
            <FormControlLabel control={<Checkbox checked={reviewed} onChange={(event) => setReviewed(event.target.checked)} />} label="I have reviewed the evidence trace." />
          )}
          <TextField sx={{ mt: 2 }} fullWidth label="Comment (optional)" multiline minRows={2} value={comment} onChange={(event) => setComment(event.target.value)} />
          {mutation.error && <Alert severity="error" sx={{ mt: 1 }}>{mutation.error.message}</Alert>}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDecision(null)}>Cancel</Button>
          <Button variant="contained" color={decision === 'reject' ? 'error' : 'primary'} disabled={mutation.isPending || (decision === 'approve' && !reviewed)} onClick={() => mutation.mutate()}>
            {mutation.isPending ? 'Recording…' : 'Confirm decision'}
          </Button>
        </DialogActions>
      </Dialog>
    </Stack>
  )
}

// --------------------------------------------------------------------------
// Tab 4 — handoffs and exports.
// --------------------------------------------------------------------------

function ExportsTab({ caseItem }: { caseItem: DecisionCase }) {
  const { user } = useSession()
  const client = useQueryClient()
  const [message, setMessage] = useState('')
  const [language, setLanguage] = useState('en')
  const [revoking, setRevoking] = useState(false)
  const [reason, setReason] = useState('')
  const contract = useQuery({
    queryKey: ['husika-contract'],
    queryFn: () => api<{ title: string; version: string; sha256: string; retrieved_at: string }>('/api/library/husika-contract'),
  })
  const refresh = () => client.invalidateQueries({ queryKey: ['case', caseItem.id] })
  const canExport = ['APPROVED', 'HANDED_OFF', 'REVOKED'].includes(caseItem.state)

  const makeExport = useMutation({
    mutationFn: ({ kind }: { kind: string }) =>
      post<{ exports: ExportRecord[] }>(`/api/cases/${caseItem.id}/exports/${kind}`, kind === 'husika' ? { message: message || undefined, language } : {}),
    onSuccess: refresh,
  })
  const handoff = useMutation({
    mutationFn: () => post<DecisionCase>(`/api/cases/${caseItem.id}/transition`, { to_state: 'HANDED_OFF', version: caseItem.version }),
    onSuccess: refresh,
  })
  const revoke = useMutation({
    mutationFn: () => post<DecisionCase>(`/api/cases/${caseItem.id}/transition`, { to_state: 'REVOKED', version: caseItem.version, reason }),
    onSuccess: () => { setRevoking(false); refresh() },
  })

  const exportCard = (title: string, description: string, kind: string, body?: ReactNode, permitted = user?.role === 'county_drm_officer') => (
    <Card sx={{ height: '100%' }}>
      <CardHeader title={title} subheader={description} titleTypographyProps={{ variant: 'subtitle1', fontWeight: 700 }} />
      <CardContent sx={{ pt: 0 }}>{body}</CardContent>
      <CardActions>
        <Tooltip title={!permitted ? 'Your role cannot generate this export' : !canExport ? 'Available after the three approvals land' : `Generate an immutable ${title}`}>
          <span>
            <Button variant="contained" startIcon={<Download />} disabled={!canExport || !permitted || makeExport.isPending} onClick={() => makeExport.mutate({ kind })}>
              Generate
            </Button>
          </span>
        </Tooltip>
      </CardActions>
    </Card>
  )

  const endpoints = [
    `/integration/v1/activations/${caseItem.id}`,
    `/integration/v1/activations/${caseItem.id}/cap.xml`,
    `/integration/v1/activations/${caseItem.id}/husika-payload.json`,
    `/integration/v1/activations/${caseItem.id}/verify`,
  ]

  return (
    <Stack spacing={2}>
      {!canExport && <Alert severity="info">Exports unlock when three role approvals move the case to APPROVED.</Alert>}

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, md: 6 }}>{exportCard('Activation Decision Packet', 'Immutable JSON manifest and PDF decision record.', 'packet')}</Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          {exportCard('CAP 1.2 alert', 'Exercise-status CAP XML; a Cancel message is generated after revocation.', 'cap', (
            <Typography variant="body2">
              Public feed: <a href="/cap/feed.xml" target="_blank" rel="noreferrer">/cap/feed.xml</a>
            </Typography>
          ))}
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          {exportCard('Husika payload', 'Validated against the vendored Husika Data Ingestor OpenAPI contract.', 'husika', (
            <Stack spacing={1}>
              <TextField
                value={message}
                onChange={(event) => setMessage(event.target.value)}
                multiline
                minRows={3}
                label="Message body"
                placeholder={`Exercise: ${caseItem.hazard} readiness action for ${caseItem.area_name}…`}
                inputProps={{ maxLength: 3000 }}
              />
              <FormControl size="small">
                <InputLabel>Language</InputLabel>
                <Select label="Language" value={language} onChange={(event) => setLanguage(event.target.value)}>
                  <MenuItem value="en">English</MenuItem>
                  <MenuItem value="sw">Swahili</MenuItem>
                </Select>
              </FormControl>
              <Alert severity="success">
                {contract.data
                  ? `Validates against ${contract.data.title} v${contract.data.version} · spec ${contract.data.sha256.slice(0, 12)}… ✓`
                  : 'Loading the Husika OpenAPI contract…'}
                <br />
                Ready for dispatch by an authorised Husika operator — Linda Protocol does not send.
              </Alert>
            </Stack>
          ), user?.role === 'county_drm_officer' || user?.role === 'ngo_finance_lead')}
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>{exportCard('Air-gapped field bundle', 'Offline dossier, packet manifest, CAP XML, and checksums in a zip.', 'bundle')}</Grid>
      </Grid>

      {makeExport.error && <ErrorPanel error={makeExport.error} />}

      {caseItem.exports.length > 0 && (
        <Card>
          <CardHeader title="Generated immutable exports" subheader="Regeneration creates a new export; previous files stay downloadable" />
          <CardContent sx={{ pt: 0 }}>
            <List dense>
              {caseItem.exports.map((item) => (
                <ListItem
                  key={item.id}
                  disableGutters
                  secondaryAction={
                    <Button component="a" href={`/api/exports/${item.id}/download`} startIcon={<Download />} size="small">Download</Button>
                  }
                >
                  <ListItemText
                    primary={item.kind.replaceAll('_', ' ')}
                    secondaryTypographyProps={{ component: 'div' }}
                    secondary={<Stack direction="row" spacing={1} alignItems="center"><HashBlock value={item.sha256} /><Typography variant="caption">{item.generated_at}</Typography></Stack>}
                  />
                </ListItem>
              ))}
            </List>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader title="Partner integration" subheader="Consumable by Husika or any partner system: read-only, verifiable, Exercise-labelled" />
        <CardContent sx={{ pt: 0 }}>
          <Stack spacing={1}>
            {endpoints.map((endpoint) => (
              <Paper key={endpoint} variant="outlined" sx={{ p: 1, display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 1 }}>
                <Typography className="mono" variant="body2" sx={{ wordBreak: 'break-all' }}>{endpoint}</Typography>
                <CopyButton value={endpoint} label="Copy endpoint" />
              </Paper>
            ))}
          </Stack>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ mt: 2 }}>
            <Button component="a" href="/integration/v1/docs" target="_blank" rel="noreferrer" startIcon={<Api />}>API documentation</Button>
            <Button component="a" href="/cap/feed.xml" target="_blank" rel="noreferrer">Public CAP feed</Button>
            <Button component={Link} to="/integrations">API &amp; Partners</Button>
          </Stack>
        </CardContent>
      </Card>

      {['APPROVED', 'HANDED_OFF'].includes(caseItem.state) && (
        <Paper sx={{ p: 2, border: 1, borderColor: 'error.main' }}>
          <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" spacing={1}>
            <Box>
              <Typography variant="h6">Handoff and revocation</Typography>
              <Typography variant="body2" color="text.secondary">
                Stop trigger armed: {String((caseItem.assessment?.stop_trigger as { condition?: string })?.condition ?? 'per policy.yaml')}. Manual
                revocation requires a recorded reason.
              </Typography>
            </Box>
            <Stack direction="row" spacing={1}>
              <Tooltip title={user?.role === 'county_drm_officer' ? 'Mark handed off after at least one export' : 'Requires County DRM Officer role'}>
                <span>
                  <Button disabled={caseItem.state !== 'APPROVED' || user?.role !== 'county_drm_officer' || handoff.isPending} onClick={() => handoff.mutate()}>
                    Mark handed off
                  </Button>
                </span>
              </Tooltip>
              <Button color="error" disabled={user?.role !== 'county_drm_officer'} onClick={() => setRevoking(true)}>Revoke</Button>
            </Stack>
          </Stack>
          {handoff.error && <ErrorPanel error={handoff.error} />}
        </Paper>
      )}

      <Dialog open={revoking} onClose={() => setRevoking(false)} fullWidth maxWidth="sm">
        <DialogTitle>Revoke activation</DialogTitle>
        <DialogContent>
          <DialogContentText sx={{ mb: 2 }}>
            This terminal transition is recorded in the audit chain and makes an Exercise CAP Cancel available.
          </DialogContentText>
          <TextField fullWidth multiline minRows={3} label="Mandatory revocation reason" value={reason} onChange={(event) => setReason(event.target.value)} />
          {revoke.error && <Alert severity="error" sx={{ mt: 1 }}>{revoke.error.message}</Alert>}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRevoking(false)}>Cancel</Button>
          <Button color="error" variant="contained" disabled={!reason.trim() || revoke.isPending} onClick={() => revoke.mutate()}>Revoke activation</Button>
        </DialogActions>
      </Dialog>
    </Stack>
  )
}

function WebhookDeliveryStatus({ caseId }: { caseId: string }) {
  const deliveries = useQuery({
    queryKey: ['webhook-deliveries', caseId],
    queryFn: () => api<{ id: string; url: string; event: string; attempt: number; status_code?: number; delivered: number; attempted_at: string }[]>(`/api/cases/${caseId}/webhook-deliveries`),
  })
  return (
    <Card>
      <CardHeader title="Webhook deliveries" subheader="Signed partner notifications emitted for this activation" />
      <CardContent sx={{ pt: 0 }}>
        {deliveries.isLoading ? (
          <Skeleton variant="rounded" height={70} />
        ) : deliveries.error ? (
          <ErrorPanel error={deliveries.error} retry={() => deliveries.refetch()} />
        ) : deliveries.data?.length ? (
          <List dense>
            {deliveries.data.map((delivery) => (
              <ListItem key={delivery.id} disableGutters>
                <ListItemText primary={`${delivery.event} · attempt ${delivery.attempt}`} secondary={`${delivery.url} · ${delivery.attempted_at}${delivery.status_code ? ` · HTTP ${delivery.status_code}` : ''}`} />
                <StateChip state={delivery.delivered ? 'DELIVERED' : 'FAILED'} />
              </ListItem>
            ))}
          </List>
        ) : (
          <EmptyState>No webhook delivery has been recorded for this activation.</EmptyState>
        )}
      </CardContent>
    </Card>
  )
}

// --------------------------------------------------------------------------
// Tab 5 — per-case audit timeline.
// --------------------------------------------------------------------------

function CaseAudit({ caseId }: { caseId: string }) {
  const events = useQuery({
    queryKey: ['events', caseId],
    queryFn: () => api<{ id: string; seq: number; actor_id: string; event_type: string; data: Record<string, unknown>; this_hash: string; created_at: string }[]>(`/api/cases/${caseId}/events`),
  })
  const verification = useQuery({
    queryKey: ['event-verification', caseId],
    queryFn: () => api<{ ok: boolean; events: number; head_hash?: string; broken_seq?: number }>(`/api/cases/${caseId}/events/verify`),
  })

  if (events.isLoading) return <Skeleton variant="rounded" height={420} />
  if (events.error) return <ErrorPanel error={events.error} retry={() => events.refetch()} />

  return (
    <Stack spacing={2}>
      <Alert
        severity={verification.data?.ok ? 'success' : verification.data ? 'error' : 'info'}
        action={<Button color="inherit" size="small" onClick={() => verification.refetch()}>Verify chain</Button>}
      >
        {verification.data?.ok
          ? `${verification.data.events} events, hash chain intact.`
          : verification.data
            ? `Chain break detected at event ${verification.data.broken_seq}.`
            : 'Verifying the event chain…'}
      </Alert>
      <Timeline position="right" sx={{ px: 0 }}>
        {events.data?.map((event) => (
          <TimelineItem key={event.id}>
            <TimelineOppositeContent color="text.secondary" variant="caption" sx={{ flex: 0.25 }}>{event.created_at}</TimelineOppositeContent>
            <TimelineSeparator>
              <TimelineDot color={/FAILED|REVOKED|CONFLICT/.test(event.event_type) ? 'error' : /APPROVAL|DELIVERED/.test(event.event_type) ? 'success' : 'primary'} />
              <TimelineConnector />
            </TimelineSeparator>
            <TimelineContent>
              <Typography fontWeight={600}>{event.event_type.replaceAll('_', ' ')}</Typography>
              <Stack direction="row" spacing={1} alignItems="center">
                <Chip size="small" variant="outlined" icon={event.actor_id.startsWith('assist:') ? <SmartToy fontSize="small" /> : undefined} label={event.actor_id} />
                <HashBlock value={event.this_hash} label="Event hash" />
              </Stack>
              <Accordion sx={{ mt: 0.5 }}>
                <AccordionSummary expandIcon={<ExpandMore />}>Payload</AccordionSummary>
                <AccordionDetails><pre>{JSON.stringify(event.data, null, 2)}</pre></AccordionDetails>
              </Accordion>
            </TimelineContent>
          </TimelineItem>
        ))}
      </Timeline>
    </Stack>
  )
}
