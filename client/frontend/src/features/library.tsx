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

type StageDefinition = { indicator: string; condition: { probability_gte: number; quantile: number; min_lead_months?: number } }
type PolicyDocument = {
  id: string
  raw: string
  data: {
    policy: {
      name: string
      disclaimer: string
      hazard: string
      ndma_phase_mapping: Record<string, string>
      stages: Record<string, StageDefinition>
      gates: { id: string; description: string }[]
      stop_trigger: { description: string; condition: { probability_lt: number; on_indicator: string } }
      cost_loss: { exposed_households: { value: number; citation: string }; loss_per_household_usd: number; margin_usd: number }
    }
  }
}

export function LibraryPage() {
  const [tab, setTab] = useState('policy')
  const policy = useQuery({ queryKey: ['policy'], queryFn: () => api<PolicyDocument>('/api/library/policy') })
  const cards = useQuery({ queryKey: ['action-library'], queryFn: () => api<ActionCard[]>('/api/library/actions') })
  const document = policy.data?.data.policy

  return (
    <Box>
      <Typography variant="h4">Policy &amp; Action Library</Typography>
      <Typography color="text.secondary" mb={2}>
        Policy files are code-reviewed, schema-validated at startup, and hash-pinned. Editing happens in git, never in this UI.
      </Typography>

      <Tabs value={tab} onChange={(_, value) => setTab(value)} sx={{ mb: 2 }}>
        <Tab value="policy" label="Policy" />
        <Tab value="actions" label={`Action cards (${cards.data?.length ?? 0})`} />
      </Tabs>

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
                              P ≥ {definition.condition.probability_gte} @q≤{definition.condition.quantile}
                              {definition.condition.min_lead_months ? `, lead ≥ ${definition.condition.min_lead_months}m` : ''}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
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
                      <strong>Stop trigger:</strong> {document?.stop_trigger.description} — revokes when P &lt;{' '}
                      {document?.stop_trigger.condition.probability_lt} on <span className="mono">{document?.stop_trigger.condition.on_indicator}</span>.
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
