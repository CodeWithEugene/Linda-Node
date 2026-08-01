import { ReactNode, useState } from 'react'
import Accordion from '@mui/material/Accordion'
import AccordionDetails from '@mui/material/AccordionDetails'
import AccordionSummary from '@mui/material/AccordionSummary'
import Alert from '@mui/material/Alert'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Chip from '@mui/material/Chip'
import Dialog from '@mui/material/Dialog'
import DialogActions from '@mui/material/DialogActions'
import DialogContent from '@mui/material/DialogContent'
import DialogTitle from '@mui/material/DialogTitle'
import IconButton from '@mui/material/IconButton'
import Paper from '@mui/material/Paper'
import Stack from '@mui/material/Stack'
import Tooltip from '@mui/material/Tooltip'
import Typography from '@mui/material/Typography'
import ContentCopy from '@mui/icons-material/ContentCopy'
import ExpandMore from '@mui/icons-material/ExpandMore'
import type { Freshness, SourceSnapshot } from './types'

export const FRESHNESS_LABEL: Record<Freshness, string> = {
  live: 'Live',
  cached: 'Cached',
  stale: 'Stale',
  replay: 'Replay',
}

export const freshnessColor = (value: string): 'success' | 'info' | 'warning' | 'default' =>
  value === 'live' ? 'success' : value === 'replay' ? 'info' : value === 'stale' || value === 'cached' ? 'warning' : 'default'

export const severityRank = (value?: string): number =>
  ({ severe: 4, high: 4, go: 4, critical: 4, moderate: 3, set: 3, watch: 3, low: 2, ready: 2, minor: 1 } as Record<string, number>)[
    (value || '').toLowerCase()
  ] ?? 0

export const severityColor = (value?: string): 'error' | 'warning' | 'info' | 'default' => {
  const rank = severityRank(value)
  return rank >= 4 ? 'error' : rank === 3 ? 'warning' : rank === 2 ? 'info' : 'default'
}

/** LinearProgress has no `default` colour, so meters fall back to primary. */
export const meterColor = (value?: string): 'error' | 'warning' | 'info' | 'primary' => {
  const rank = severityRank(value)
  return rank >= 4 ? 'error' : rank === 3 ? 'warning' : rank === 2 ? 'info' : 'primary'
}

export function relativeTime(value?: string): string {
  if (!value) return '—'
  const hours = Math.round((new Date(value).getTime() - Date.now()) / 3_600_000)
  if (Math.abs(hours) < 1) return 'just now'
  if (Math.abs(hours) < 48) return new Intl.RelativeTimeFormat('en', { numeric: 'auto' }).format(hours, 'hour')
  return new Intl.RelativeTimeFormat('en', { numeric: 'auto' }).format(Math.round(hours / 24), 'day')
}

export function FreshnessBadge({ value, retrievedAt }: { value: string; retrievedAt?: string }) {
  return (
    <Tooltip title={retrievedAt ? `Retrieved ${retrievedAt}` : 'Source freshness'}>
      <Chip size="small" label={FRESHNESS_LABEL[value as Freshness] ?? value} color={freshnessColor(value)} variant={value === 'live' ? 'filled' : 'outlined'} />
    </Tooltip>
  )
}

export function StateChip({ state }: { state: string }) {
  const color =
    state === 'APPROVED' || state === 'RESOLVED' || state === 'HANDED_OFF' || state === 'DELIVERED'
      ? 'success'
      : state === 'BLOCKED' || state === 'REVOKED' || state === 'REJECTED' || state === 'DECLINED' || state === 'FAILED'
        ? 'error'
        : state === 'READY_FOR_REVIEW' || state === 'SET' || state === 'ACKNOWLEDGED'
          ? 'warning'
          : 'default'
  return <Chip size="small" label={state.replaceAll('_', ' ')} color={color} />
}

/** A stage of `null` means the deterministic engine reached no stage at all. */
export function StageChip({ stage, ndmaPhase }: { stage?: string | null; ndmaPhase?: string | null }) {
  if (!stage) {
    return (
      <Tooltip title="No stage condition in policy.yaml was met by the attached evidence">
        <Chip size="small" variant="outlined" label="No activation recommended" />
      </Tooltip>
    )
  }
  return <Chip size="small" color={severityColor(stage)} label={`${stage.toUpperCase()}${ndmaPhase ? ` · NDMA: ${ndmaPhase}` : ''}`} />
}

export function CopyButton({ value, label = 'Copy' }: { value: string; label?: string }) {
  const [copied, setCopied] = useState(false)
  return (
    <Tooltip title={copied ? 'Copied' : label}>
      <IconButton
        size="small"
        aria-label={label}
        onClick={() => {
          navigator.clipboard.writeText(value).then(() => setCopied(true))
          window.setTimeout(() => setCopied(false), 1500)
        }}
      >
        <ContentCopy fontSize="inherit" />
      </IconButton>
    </Tooltip>
  )
}

export function HashBlock({ value, label = 'SHA-256' }: { value?: string; label?: string }) {
  if (!value) return <Typography variant="caption" color="text.secondary">—</Typography>
  return (
    <Tooltip title={`${label}: ${value}`}>
      <Box component="span" sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.25 }}>
        <Typography component="span" className="mono" variant="caption">
          {value.slice(0, 8)}…{value.slice(-4)}
        </Typography>
        <CopyButton value={value} label={`Copy ${label}`} />
      </Box>
    </Tooltip>
  )
}

export function RoleLabel({ role }: { role: string }) {
  return <>{role.replaceAll('_', ' ').replace(/\b\w/g, (character) => character.toUpperCase())}</>
}

export function ErrorPanel({ error, retry }: { error: unknown; retry?: () => void }) {
  return (
    <Alert severity="error" action={retry ? <Button color="inherit" size="small" onClick={retry}>Retry</Button> : undefined}>
      {error instanceof Error ? error.message : 'Something went wrong.'}
    </Alert>
  )
}

export function EmptyState({ children, action }: { children: ReactNode; action?: ReactNode }) {
  return (
    <Stack spacing={1.5} sx={{ py: 6, px: 3, textAlign: 'center', color: 'text.secondary', alignItems: 'center' }}>
      <Typography variant="body2">{children}</Typography>
      {action}
    </Stack>
  )
}

export function ProvenanceLegend() {
  return (
    <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
      <Chip size="small" color="success" label="Official source" />
      <Chip size="small" color="warning" label="Policy assumption" />
      <Chip size="small" color="info" label="User entered" />
      <Chip size="small" variant="outlined" label="Dashed border = AI output" />
    </Stack>
  )
}

const numberFormat = new Intl.NumberFormat('en-US')
export const money = (amount: number, currency = 'USD') =>
  `${currency === 'USD' ? '$' : `${currency} `}${numberFormat.format(amount)}`

/**
 * Provenance dialog. Raw upstream bodies can be megabytes, so the server sends
 * a bounded, email-masked preview alongside the per-endpoint hashes a reviewer
 * needs to verify the full body with `curl <url> | shasum -a 256`.
 */
export function SnapshotDialog({ snapshot, onClose }: { snapshot: SourceSnapshot | null; onClose: () => void }) {
  const parts = snapshot?.meta?.parts ?? []
  const provenance = snapshot?.meta?.provenance
  return (
    <Dialog open={Boolean(snapshot)} onClose={onClose} fullWidth maxWidth="md">
      <DialogTitle>Source provenance</DialogTitle>
      <DialogContent dividers>
        {snapshot && (
          <Stack spacing={2}>
            <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
              <FreshnessBadge value={snapshot.freshness} retrievedAt={snapshot.retrieved_at} />
              <Chip
                size="small"
                color={snapshot.schema_ok ? 'success' : 'error'}
                label={snapshot.schema_ok ? 'Schema valid' : 'Schema invalid'}
              />
              {snapshot.meta?.synthetic || provenance?.synthetic ? <Chip size="small" color="info" label="Synthetic fixture" /> : null}
              <Typography variant="body2" color="text.secondary">
                Retrieved {snapshot.retrieved_at}
              </Typography>
            </Stack>

            {provenance?.note && <Alert severity="info">{provenance.note}</Alert>}
            {snapshot.meta?.schema_errors?.length ? (
              <Alert severity="error">
                Schema validation failed: {snapshot.meta.schema_errors.join('; ')}
              </Alert>
            ) : null}
            {snapshot.meta?.last_error && <Alert severity="warning">Upstream error: {snapshot.meta.last_error}</Alert>}

            <Paper variant="outlined" sx={{ p: 1.5 }}>
              <Typography variant="overline" color="text.secondary">Snapshot hash</Typography>
              <Stack direction="row" alignItems="center" spacing={0.5}>
                <Typography className="mono" variant="body2" sx={{ wordBreak: 'break-all' }}>{snapshot.payload_sha256}</Typography>
                <CopyButton value={snapshot.payload_sha256} label="Copy snapshot hash" />
              </Stack>
            </Paper>

            <Box>
              <Typography variant="overline" color="text.secondary">Upstream responses</Typography>
              <Stack spacing={1}>
                {(parts.length ? parts : [{ url: snapshot.endpoint_url, sha256: snapshot.payload_sha256, bytes: 0 }]).map((part) => (
                  <Paper key={part.url} variant="outlined" sx={{ p: 1.25 }}>
                    <Stack direction="row" alignItems="center" justifyContent="space-between" spacing={1}>
                      <Typography className="mono" variant="caption" sx={{ wordBreak: 'break-all' }}>{part.url}</Typography>
                      <CopyButton value={part.url} label="Copy endpoint URL" />
                    </Stack>
                    <Stack direction="row" alignItems="center" spacing={0.5}>
                      <Typography className="mono" variant="caption" color="text.secondary" sx={{ wordBreak: 'break-all' }}>
                        {part.sha256}
                      </Typography>
                      <CopyButton value={part.sha256} label="Copy body hash" />
                    </Stack>
                    {part.bytes ? (
                      <Typography variant="caption" color="text.secondary">
                        {(part.bytes / 1024).toFixed(1)} KB · verify with <span className="mono">curl {part.url.startsWith('http') ? '<url>' : '<file>'} | shasum -a 256</span>
                      </Typography>
                    ) : null}
                  </Paper>
                ))}
              </Stack>
            </Box>

            <Accordion>
              <AccordionSummary expandIcon={<ExpandMore />}>Verbatim upstream body (email addresses masked)</AccordionSummary>
              <AccordionDetails>
                {snapshot.raw?.available ? (
                  <>
                    {snapshot.raw.truncated && (
                      <Alert severity="info" sx={{ mb: 1 }}>
                        Showing the first {Math.round((snapshot.raw.preview?.length ?? 0) / 1000)} KB of {((snapshot.raw.bytes ?? 0) / 1024).toFixed(0)} KB. The hash above covers the whole body.
                      </Alert>
                    )}
                    <pre>{snapshot.raw.preview}</pre>
                  </>
                ) : (
                  <Typography variant="body2" color="text.secondary">{snapshot.raw?.note ?? 'No verbatim body retained for this snapshot.'}</Typography>
                )}
              </AccordionDetails>
            </Accordion>

            <Accordion>
              <AccordionSummary expandIcon={<ExpandMore />}>Normalised view used by the workflow</AccordionSummary>
              <AccordionDetails>
                <pre>{JSON.stringify(snapshot.payload, null, 2)}</pre>
              </AccordionDetails>
            </Accordion>
          </Stack>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  )
}
