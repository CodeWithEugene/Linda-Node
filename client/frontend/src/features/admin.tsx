import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import Alert from '@mui/material/Alert'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Card from '@mui/material/Card'
import CardContent from '@mui/material/CardContent'
import CardHeader from '@mui/material/CardHeader'
import Chip from '@mui/material/Chip'
import FormControl from '@mui/material/FormControl'
import Grid from '@mui/material/Grid2'
import InputLabel from '@mui/material/InputLabel'
import List from '@mui/material/List'
import ListItem from '@mui/material/ListItem'
import ListItemText from '@mui/material/ListItemText'
import MenuItem from '@mui/material/MenuItem'
import Paper from '@mui/material/Paper'
import Select from '@mui/material/Select'
import Slider from '@mui/material/Slider'
import Stack from '@mui/material/Stack'
import TextField from '@mui/material/TextField'
import Typography from '@mui/material/Typography'
import Replay from '@mui/icons-material/Replay'
import { api, del, post } from '../api'
import type { DecisionCase } from '../api'
import { CopyButton, EmptyState, ErrorPanel } from '../components'
import type { SourceStatus } from '../types'

const ESCALATION_LABELS = ['Recorded ICPAC statistics', 'Synthetic step 1 · P 0.32 (below READY)', 'Synthetic step 2 · P 0.52 (SET)', 'Synthetic step 3 · P 0.63 (GO)']

export function AdminPage() {
  const client = useQueryClient()
  const [keyLabel, setKeyLabel] = useState('Partner console')
  const [issued, setIssued] = useState<string | null>(null)
  const [url, setUrl] = useState('https://webhook.site/replace-me')
  const [secret, setSecret] = useState('replace-with-at-least-16-characters')
  const [events, setEvents] = useState<string[]>(['activation.approved', 'activation.revoked'])
  const [mode, setMode] = useState('live_first')
  const [step, setStep] = useState(2)
  const [caseId, setCaseId] = useState('')
  const [probability, setProbability] = useState('0.22')

  const keys = useQuery({ queryKey: ['integration-keys'], queryFn: () => api<{ id: string; label: string; created_at: string; revoked_at?: string }[]>('/api/admin/integration-keys') })
  const hooks = useQuery({ queryKey: ['webhooks'], queryFn: () => api<{ id: string; url: string; events: string[]; active: number; last_delivery?: { delivered: number; status_code?: number; attempted_at: string } }[]>('/api/admin/webhooks') })
  const status = useQuery({ queryKey: ['sources-status'], queryFn: () => api<SourceStatus>('/api/sources/status') })
  const cases = useQuery({ queryKey: ['admin-cases'], queryFn: () => api<Pick<DecisionCase, 'id' | 'title' | 'state'>[]>('/api/cases') })

  const refreshKeys = () => {
    client.invalidateQueries({ queryKey: ['integration-keys'] })
    client.invalidateQueries({ queryKey: ['webhooks'] })
  }
  const invalidateSources = () => {
    for (const key of ['sources-status', 'signals', 'areas']) client.invalidateQueries({ queryKey: [key] })
  }

  const keyMutation = useMutation({ mutationFn: () => post<{ id: string; key: string }>('/api/admin/integration-keys', { label: keyLabel }), onSuccess: (result) => { setIssued(result.key); refreshKeys() } })
  const hookMutation = useMutation({ mutationFn: () => post('/api/admin/webhooks', { url, events, secret }), onSuccess: refreshKeys })
  const modeMutation = useMutation({ mutationFn: () => post<{ mode: string }>('/api/admin/replay-mode', { mode }), onSuccess: invalidateSources })
  const stepMutation = useMutation({ mutationFn: () => post<{ step: number }>('/api/admin/replay-step', { step }), onSuccess: invalidateSources })
  const stopMutation = useMutation({
    mutationFn: () => post<DecisionCase & { stop_trigger?: { fired: boolean; condition: string } }>('/api/admin/simulate-stop-trigger', { case_id: caseId, observed_probability: Number(probability) }),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ['cases'] })
      client.invalidateQueries({ queryKey: ['admin-cases'] })
      client.invalidateQueries({ queryKey: ['case', caseId] })
    },
  })
  const reset = useMutation({ mutationFn: () => post('/api/admin/seed'), onSuccess: () => { client.clear(); window.location.assign('/') } })

  useEffect(() => {
    if (status.data?.mode) setMode(status.data.mode)
    if (status.data?.escalation_step !== undefined) setStep(status.data.escalation_step)
  }, [status.data?.mode, status.data?.escalation_step])

  return (
    <Stack spacing={3}>
      <Box>
        <Typography variant="h4">Admin</Typography>
        <Typography color="text.secondary">Source mode, the labelled escalation sequence, demo recovery, partner keys, and signed webhooks.</Typography>
      </Box>

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, md: 6 }}>
          <Card sx={{ height: '100%' }}>
            <CardHeader title="Integration API keys" subheader="A key is shown once. Partner routes are limited to 60 requests/minute/key." />
            <CardContent sx={{ pt: 0 }}>
              <Stack spacing={1.5}>
                <TextField label="Key label" value={keyLabel} onChange={(event) => setKeyLabel(event.target.value)} />
                <Button variant="contained" onClick={() => keyMutation.mutate()} disabled={keyMutation.isPending}>Create API key</Button>
                {issued && (
                  <Alert severity="warning">
                    Copy this now — it will not be shown again.
                    <Stack direction="row" alignItems="center" spacing={0.5}>
                      <Typography className="mono" variant="caption" sx={{ wordBreak: 'break-all' }}>{issued}</Typography>
                      <CopyButton value={issued} label="Copy API key" />
                    </Stack>
                  </Alert>
                )}
                {keyMutation.error && <ErrorPanel error={keyMutation.error} />}
                {keys.data?.length ? (
                  <List dense>
                    {keys.data.map((key) => (
                      <ListItem
                        key={key.id}
                        disableGutters
                        secondaryAction={!key.revoked_at ? <Button size="small" color="error" onClick={() => del<void>(`/api/admin/integration-keys/${key.id}`).then(refreshKeys)}>Revoke</Button> : undefined}
                      >
                        <ListItemText primary={key.label} secondary={key.revoked_at ? `Revoked ${key.revoked_at}` : `Created ${key.created_at}`} />
                      </ListItem>
                    ))}
                  </List>
                ) : (
                  <EmptyState>No partner keys issued yet.</EmptyState>
                )}
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, md: 6 }}>
          <Card sx={{ height: '100%' }}>
            <CardHeader title="Webhook subscriptions" subheader="Approved or revoked activations are signed with X-Linda-Signature." />
            <CardContent sx={{ pt: 0 }}>
              <Stack spacing={1.5}>
                <TextField label="Webhook URL" value={url} onChange={(event) => setUrl(event.target.value)} helperText="Public HTTPS only; loopback and private ranges are rejected." />
                <TextField label="Webhook secret" value={secret} onChange={(event) => setSecret(event.target.value)} helperText="At least 16 characters." />
                <FormControl size="small">
                  <InputLabel>Events</InputLabel>
                  <Select multiple label="Events" value={events} onChange={(event) => setEvents(event.target.value as string[])}>
                    {['activation.approved', 'activation.revoked'].map((item) => <MenuItem key={item} value={item}>{item}</MenuItem>)}
                  </Select>
                </FormControl>
                <Button variant="contained" onClick={() => hookMutation.mutate()} disabled={hookMutation.isPending}>Register webhook</Button>
                {hookMutation.error && <ErrorPanel error={hookMutation.error} />}
                {hooks.data?.length ? (
                  <List dense>
                    {hooks.data.map((hook) => (
                      <ListItem key={hook.id} disableGutters secondaryAction={<Button size="small" color="error" onClick={() => del<void>(`/api/admin/webhooks/${hook.id}`).then(refreshKeys)}>Remove</Button>}>
                        <ListItemText
                          primary={hook.url}
                          secondary={`${hook.events.join(', ')} · ${hook.last_delivery ? (hook.last_delivery.delivered ? 'Delivered' : `Last failed (${hook.last_delivery.status_code || 'network'})`) : 'No delivery yet'}`}
                        />
                      </ListItem>
                    ))}
                  </List>
                ) : (
                  <EmptyState>No webhook subscriptions registered.</EmptyState>
                )}
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, md: 6 }}>
          <Card sx={{ height: '100%' }}>
            <CardHeader title="Evidence source mode" subheader="The active mode is always visible to the workspace." />
            <CardContent sx={{ pt: 0 }}>
              <Stack spacing={2}>
                <FormControl size="small">
                  <InputLabel>Mode</InputLabel>
                  <Select label="Mode" value={mode} onChange={(event) => setMode(event.target.value)}>
                    <MenuItem value="live_first">Live first</MenuItem>
                    <MenuItem value="replay_only">Replay only</MenuItem>
                  </Select>
                </FormControl>
                <Button variant="contained" disabled={status.isLoading || modeMutation.isPending} onClick={() => modeMutation.mutate()}>
                  {modeMutation.isPending ? 'Saving…' : 'Apply mode'}
                </Button>
                {modeMutation.error && <ErrorPanel error={modeMutation.error} />}
                <Paper variant="outlined" sx={{ p: 1.5 }}>
                  <Typography variant="overline" color="text.secondary">Synthetic escalation sequence</Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                    Applies in replay-only mode. Steps 1–3 are team-authored Bungoma probabilities that exercise the READY/SET/GO
                    thresholds; every other admin row stays the recorded ICPAC statistic.
                  </Typography>
                  <Slider value={step} onChange={(_, value) => setStep(value as number)} min={0} max={3} step={1} marks valueLabelDisplay="auto" />
                  <Chip size="small" color={step ? 'info' : 'success'} label={ESCALATION_LABELS[step]} sx={{ mb: 1 }} />
                  <Button fullWidth variant="outlined" disabled={stepMutation.isPending} onClick={() => stepMutation.mutate()}>
                    {stepMutation.isPending ? 'Applying…' : 'Apply escalation step'}
                  </Button>
                  {stepMutation.error && <ErrorPanel error={stepMutation.error} />}
                </Paper>
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, md: 6 }}>
          <Card sx={{ height: '100%' }}>
            <CardHeader title="Stop-trigger evaluation" subheader="Injects an observation; policy.yaml decides whether to revoke." />
            <CardContent sx={{ pt: 0 }}>
              <Stack spacing={1.5}>
                <FormControl size="small">
                  <InputLabel>Case</InputLabel>
                  <Select label="Case" value={caseId} onChange={(event) => setCaseId(event.target.value)}>
                    {cases.data?.filter((item) => ['APPROVED', 'HANDED_OFF'].includes(item.state)).map((item) => (
                      <MenuItem key={item.id} value={item.id}>{item.title} · {item.state}</MenuItem>
                    ))}
                  </Select>
                </FormControl>
                <TextField
                  label="Observed probability"
                  type="number"
                  value={probability}
                  onChange={(event) => setProbability(event.target.value)}
                  inputProps={{ min: 0, max: 1, step: 0.01 }}
                  helperText="Above the policy threshold the case is left alone — and the evaluation is still recorded."
                />
                <Button color="error" variant="contained" disabled={!caseId || stopMutation.isPending} onClick={() => stopMutation.mutate()}>
                  {stopMutation.isPending ? 'Evaluating…' : 'Evaluate stop trigger'}
                </Button>
                {stopMutation.data && (
                  <Alert severity={stopMutation.data.state === 'REVOKED' ? 'error' : 'success'}>
                    {stopMutation.data.state === 'REVOKED'
                      ? `Stop trigger fired (${stopMutation.data.stop_trigger?.condition}) — case revoked.`
                      : `Observation recorded; ${stopMutation.data.stop_trigger?.condition ?? 'the condition'} was not met, so the case stands.`}
                  </Alert>
                )}
                {stopMutation.error && <ErrorPanel error={stopMutation.error} />}
              </Stack>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Paper sx={{ p: 2, border: 1, borderColor: 'warning.main' }}>
        <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" alignItems={{ sm: 'center' }} spacing={1}>
          <Box>
            <Typography variant="h6">Demo recovery</Typography>
            <Typography variant="body2" color="text.secondary">
              Restores the three seeded cases — blocked, completed with all four exports, and revoked. This replaces local demo data.
            </Typography>
          </Box>
          <Button startIcon={<Replay />} color="warning" variant="contained" disabled={reset.isPending} onClick={() => reset.mutate()}>
            {reset.isPending ? 'Resetting…' : 'Restore seed data'}
          </Button>
        </Stack>
      </Paper>
    </Stack>
  )
}
