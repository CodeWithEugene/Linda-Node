import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import Accordion from '@mui/material/Accordion'
import AccordionDetails from '@mui/material/AccordionDetails'
import AccordionSummary from '@mui/material/AccordionSummary'
import Alert from '@mui/material/Alert'
import Box from '@mui/material/Box'
import Card from '@mui/material/Card'
import CardContent from '@mui/material/CardContent'
import CardHeader from '@mui/material/CardHeader'
import Chip from '@mui/material/Chip'
import Grid from '@mui/material/Grid2'
import List from '@mui/material/List'
import ListItem from '@mui/material/ListItem'
import ListItemText from '@mui/material/ListItemText'
import Paper from '@mui/material/Paper'
import Skeleton from '@mui/material/Skeleton'
import Stack from '@mui/material/Stack'
import Tab from '@mui/material/Tab'
import Table from '@mui/material/Table'
import TableBody from '@mui/material/TableBody'
import TableCell from '@mui/material/TableCell'
import TableHead from '@mui/material/TableHead'
import TableRow from '@mui/material/TableRow'
import Tabs from '@mui/material/Tabs'
import Typography from '@mui/material/Typography'
import ExpandMore from '@mui/icons-material/ExpandMore'
import { api } from '../api'
import type { ActionCard } from '../api'
import { ErrorPanel, HashBlock, money } from '../components'
import type { IndicatorRegistry } from '../types'

type StageDefinition = { indicator: string; condition: { probability_gte?: number; quantile?: number; min_lead_months?: number; upstream_severity_in?: string[] } }
type PolicyDocument = {
  id: string
  raw: string
  data: {
    policy: {
      name: string
      disclaimer: string
      hazard: string
      signal_basis?: 'probability' | 'upstream_severity'
      ndma_phase_mapping: Record<string, string>
      stages: Record<string, StageDefinition>
      gates: { id: string; description: string }[]
      stop_trigger: { description: string; condition: { probability_lt?: number; on_indicator: string; resolved_upstream?: boolean } }
      cost_loss: { exposed_households: { value: number; citation: string }; loss_per_household_usd: number; margin_usd: number }
    }
  }
}

const HAZARDS = ['drought', 'heat', 'flood'] as const

export function LibraryPage() {
  const [tab, setTab] = useState('policy')
  const [hazard, setHazard] = useState<(typeof HAZARDS)[number]>('drought')
  const policy = useQuery({ queryKey: ['policy', hazard], queryFn: () => api<PolicyDocument>(`/api/library/policy?hazard=${hazard}`) })
  const cards = useQuery({ queryKey: ['action-library'], queryFn: () => api<ActionCard[]>('/api/library/actions') })
  const indicators = useQuery({ queryKey: ['indicators'], queryFn: () => api<IndicatorRegistry>('/api/library/indicators') })
  const document = policy.data?.data.policy

  return (
    <Box>
      <Typography variant="h4">Policy &amp; Action Library</Typography>
      <Typography color="text.secondary" mb={2}>
        Policy files are code-reviewed, schema-validated at startup, and hash-pinned. Editing happens in git, never in this UI.
      </Typography>

      <Tabs value={tab} onChange={(_, value) => setTab(value)} sx={{ mb: 2 }}>
        <Tab value="policy" label="Policies" />
        <Tab value="actions" label={`Action cards (${cards.data?.length ?? 0})`} />
        <Tab value="indicators" label={`ICPAC indicators (${indicators.data?.indicators.length ?? 0})`} />
      </Tabs>

      {tab === 'policy' && (
        <Tabs value={hazard} onChange={(_, value) => setHazard(value)} sx={{ mb: 2 }} textColor="secondary" indicatorColor="secondary">
          {HAZARDS.map((item) => <Tab key={item} value={item} label={item} sx={{ textTransform: 'capitalize' }} />)}
        </Tabs>
      )}

      {tab === 'policy' &&
        (policy.isLoading ? (
          <Skeleton variant="rounded" height={420} />
        ) : policy.error ? (
          <ErrorPanel error={policy.error} retry={() => policy.refetch()} />
        ) : (
          <Grid container spacing={2}>
            <Grid size={{ xs: 12, md: 6 }}>
              <Stack spacing={2}>
                <Alert severity="warning">{document?.disclaimer}</Alert>
                <Card>
                  <CardHeader
                    title="Ready–Set–Go thresholds"
                    subheader={<Stack direction="row" spacing={0.5} alignItems="center"><span>Version</span><HashBlock value={policy.data?.id} label="Policy hash" /></Stack>}
                  />
                  <CardContent sx={{ pt: 0 }}>
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>Stage</TableCell>
                          <TableCell>NDMA phase</TableCell>
                          <TableCell>Condition</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {Object.entries(document?.stages ?? {}).map(([name, definition]) => (
                          <TableRow key={name}>
                            <TableCell><strong>{name.toUpperCase()}</strong></TableCell>
                            <TableCell>{document?.ndma_phase_mapping?.[name]}</TableCell>
                            <TableCell className="mono">
                              {definition.condition.upstream_severity_in
                                ? `ICPAC severity_level ∈ {${definition.condition.upstream_severity_in.join(', ')}}`
                                : `P ≥ ${definition.condition.probability_gte} @q≤${definition.condition.quantile}${definition.condition.min_lead_months ? `, lead ≥ ${definition.condition.min_lead_months}m` : ''}`}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                    {document?.signal_basis === 'upstream_severity' && (
                      <Alert severity="info" sx={{ mt: 1.5 }}>
                        {document.hazard} readiness follows ICPAC&rsquo;s own detected trigger events: {document.hazard === 'heat' ? 'TMAX' : 'rainfall'} is
                        published as a monitoring indicator, not a forecast one. Linda maps their <span className="mono">severity_level</span> to a
                        stage and never classifies severity itself.
                      </Alert>
                    )}
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader title="Gates and stop trigger" />
                  <CardContent sx={{ pt: 0 }}>
                    <List dense>
                      {document?.gates.map((gate) => (
                        <ListItem key={gate.id} disableGutters>
                          <ListItemText primary={gate.id.replaceAll('_', ' ')} secondary={gate.description} />
                        </ListItem>
                      ))}
                    </List>
                    <Alert severity="info">
                      <strong>Stop trigger:</strong> {document?.stop_trigger.description} —{' '}
                      {document?.stop_trigger.condition.resolved_upstream
                        ? 'revokes when the upstream trigger event is no longer active'
                        : `revokes when P < ${document?.stop_trigger.condition.probability_lt}`}{' '}
                      on <span className="mono">{document?.stop_trigger.condition.on_indicator}</span>.
                    </Alert>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader title="Cost–loss assumptions" subheader="Policy assumptions, not official figures" />
                  <CardContent sx={{ pt: 0 }}>
                    <Typography variant="body2">Exposed households: {document?.cost_loss.exposed_households.value.toLocaleString()}</Typography>
                    <Typography variant="caption" color="text.secondary">{document?.cost_loss.exposed_households.citation}</Typography>
                    <Typography variant="body2" sx={{ mt: 1 }}>Loss per household: {money(document?.cost_loss.loss_per_household_usd ?? 0)}</Typography>
                    <Typography variant="body2">Required net-benefit margin: {money(document?.cost_loss.margin_usd ?? 0)}</Typography>
                  </CardContent>
                </Card>
              </Stack>
            </Grid>
            <Grid size={{ xs: 12, md: 6 }}>
              <Card sx={{ height: '100%' }}>
                <CardHeader title="policy.yaml" subheader="The exact file the engine hash-pins at runtime" />
                <CardContent sx={{ pt: 0 }}>
                  <Paper variant="outlined" sx={{ p: 1.5, maxHeight: 680, overflow: 'auto' }}>
                    <pre className="mono">{policy.data?.raw}</pre>
                  </Paper>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        ))}

      {tab === 'indicators' &&
        (indicators.isLoading ? (
          <Skeleton variant="rounded" height={300} />
        ) : indicators.error ? (
          <ErrorPanel error={indicators.error} retry={() => indicators.refetch()} />
        ) : (
          <Card>
            <CardHeader
              title="ICPAC indicator registry"
              subheader="Read live from /api/datasets/indicators/ — this is what constrains which hazards can be forecast at all"
            />
            <CardContent sx={{ pt: 0 }}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Indicator</TableCell>
                    <TableCell>Code</TableCell>
                    <TableCell>Category</TableCell>
                    <TableCell>Unit</TableCell>
                    <TableCell>Forecast</TableCell>
                    <TableCell>Monitoring</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {indicators.data?.indicators.map((item) => (
                    <TableRow key={item.code}>
                      <TableCell>{item.name}</TableCell>
                      <TableCell className="mono">{item.code}</TableCell>
                      <TableCell><Chip size="small" label={item.category} /></TableCell>
                      <TableCell>{item.unit}</TableCell>
                      <TableCell>
                        <Chip size="small" color={item.supports_forecast ? 'success' : 'default'} label={item.supports_forecast ? 'yes' : 'no'} />
                      </TableCell>
                      <TableCell>
                        <Chip size="small" color={item.supports_monitoring ? 'success' : 'default'} label={item.supports_monitoring ? 'yes' : 'no'} />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              <Typography variant="caption" color="text.secondary">
                Only SPI-3 / CHIRPS supports seasonal forecasting, which is why drought readiness is probability-driven while heat and
                flood readiness follow detected trigger events.
              </Typography>
            </CardContent>
          </Card>
        ))}

      {tab === 'actions' &&
        (cards.isLoading ? (
          <Skeleton variant="rounded" height={420} />
        ) : cards.error ? (
          <ErrorPanel error={cards.error} retry={() => cards.refetch()} />
        ) : (
          <Grid container spacing={2}>
            {cards.data?.map((card) => (
              <Grid key={card.id} size={{ xs: 12, md: 6 }}>
                <Card sx={{ height: '100%' }}>
                  <CardHeader
                    title={card.title}
                    subheader={<Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
                      <Chip size="small" label={card.hazard} />
                      <Chip size="small" color="warning" label={card.stage_required.toUpperCase()} />
                      <Chip size="small" variant="outlined" label={`${card.lead_time_days}d lead`} />
                      <HashBlock value={card.version_hash} label="Card hash" />
                    </Stack>}
                  />
                  <CardContent sx={{ pt: 0 }}>
                    <Typography variant="body2">{card.description}</Typography>
                    <Typography variant="body2" sx={{ mt: 1 }}>
                      <strong>Tranches:</strong> {money(card.budget.readiness_tranche.amount, card.budget.currency)} at{' '}
                      {card.budget.readiness_tranche.released_at_stage.toUpperCase()} ·{' '}
                      {money(card.budget.action_tranche.amount, card.budget.currency)} at {card.budget.action_tranche.released_at_stage.toUpperCase()}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">{card.disclaimer}</Typography>
                    <Accordion sx={{ mt: 1 }}>
                      <AccordionSummary expandIcon={<ExpandMore />}>Raw YAML</AccordionSummary>
                      <AccordionDetails><pre className="mono">{card.raw}</pre></AccordionDetails>
                    </Accordion>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        ))}
    </Box>
  )
}
