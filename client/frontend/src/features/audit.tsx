import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import Box from '@mui/material/Box'
import Grid from '@mui/material/Grid2'
import Paper from '@mui/material/Paper'
import Skeleton from '@mui/material/Skeleton'
import TextField from '@mui/material/TextField'
import Typography from '@mui/material/Typography'
import { DataGrid, GridColDef } from '@mui/x-data-grid'
import { api } from '../api'
import { EmptyState, ErrorPanel, HashBlock } from '../components'

type AuditEvent = {
  id: string
  seq: number
  case_id: string
  actor_id: string
  event_type: string
  created_at: string
  this_hash: string
}

export function AuditPage() {
  const query = useQuery({ queryKey: ['global-audit'], queryFn: () => api<AuditEvent[]>('/api/audit') })
  const [caseFilter, setCaseFilter] = useState('')
  const [actorFilter, setActorFilter] = useState('')
  const [eventFilter, setEventFilter] = useState('')
  const [from, setFrom] = useState('')
  const [to, setTo] = useState('')

  const rows = useMemo(
    () =>
      (query.data ?? []).filter(
        (event) =>
          (!caseFilter || event.case_id.toLowerCase().includes(caseFilter.toLowerCase())) &&
          (!actorFilter || event.actor_id.toLowerCase().includes(actorFilter.toLowerCase())) &&
          (!eventFilter || event.event_type.toLowerCase().includes(eventFilter.toLowerCase())) &&
          (!from || event.created_at >= from) &&
          (!to || event.created_at <= `${to}T23:59:59Z`),
      ),
    [query.data, caseFilter, actorFilter, eventFilter, from, to],
  )

  const columns: GridColDef[] = [
    { field: 'seq', headerName: '#', width: 70 },
    { field: 'case_id', headerName: 'Case', minWidth: 210, flex: 1 },
    { field: 'event_type', headerName: 'Event', minWidth: 190 },
    { field: 'actor_id', headerName: 'Actor', minWidth: 150 },
    { field: 'created_at', headerName: 'Time', minWidth: 180 },
    { field: 'this_hash', headerName: 'Hash', minWidth: 170, renderCell: ({ value }) => <HashBlock value={String(value)} label="Event hash" /> },
  ]

  return (
    <Box>
      <Typography variant="h4" gutterBottom>Audit Log</Typography>
      <Typography color="text.secondary" mb={2}>
        Append-only, hash-chained case events. Every role can read and filter the full history; nothing here can be edited or deleted.
      </Typography>
      <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
        <Grid container spacing={1}>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}><TextField fullWidth label="Case" value={caseFilter} onChange={(event) => setCaseFilter(event.target.value)} /></Grid>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}><TextField fullWidth label="Actor" value={actorFilter} onChange={(event) => setActorFilter(event.target.value)} /></Grid>
          <Grid size={{ xs: 12, sm: 6, md: 2 }}><TextField fullWidth label="Event type" value={eventFilter} onChange={(event) => setEventFilter(event.target.value)} /></Grid>
          <Grid size={{ xs: 6, sm: 3, md: 2 }}><TextField fullWidth label="From" type="date" value={from} onChange={(event) => setFrom(event.target.value)} InputLabelProps={{ shrink: true }} /></Grid>
          <Grid size={{ xs: 6, sm: 3, md: 2 }}><TextField fullWidth label="To" type="date" value={to} onChange={(event) => setTo(event.target.value)} InputLabelProps={{ shrink: true }} /></Grid>
        </Grid>
      </Paper>
      {query.isLoading ? (
        <Skeleton variant="rounded" height={480} />
      ) : query.error ? (
        <ErrorPanel error={query.error} retry={() => query.refetch()} />
      ) : rows.length === 0 ? (
        <EmptyState>No audit events match these filters.</EmptyState>
      ) : (
        <Paper sx={{ height: 560 }}>
          <DataGrid rows={rows} columns={columns} disableRowSelectionOnClick sx={{ border: 0 }} />
        </Paper>
      )}
    </Box>
  )
}
