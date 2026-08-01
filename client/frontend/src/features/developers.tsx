import { useState } from 'react'
import { Link } from 'react-router-dom'
import Alert from '@mui/material/Alert'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Card from '@mui/material/Card'
import CardContent from '@mui/material/CardContent'
import CardHeader from '@mui/material/CardHeader'
import Chip from '@mui/material/Chip'
import Grid from '@mui/material/Grid2'
import Paper from '@mui/material/Paper'
import Stack from '@mui/material/Stack'
import Tab from '@mui/material/Tab'
import Tabs from '@mui/material/Tabs'
import Typography from '@mui/material/Typography'
import Api from '@mui/icons-material/Api'
import { CopyButton } from '../components'
import { Logo } from '../Logo'

const ENDPOINTS: [string, string, string, string][] = [
  ['GET', '/cap/feed.xml', 'Public', 'CAP 1.2 Atom feed of approved and revoked exercise activations.'],
  ['GET', '/integration/v1/openapi.json', 'Public', 'Machine-readable OpenAPI contract for the versioned integration surface.'],
  ['GET', '/integration/v1/schemas/activation.json', 'Public', 'JSON Schema for a published activation record.'],
  ['GET', '/integration/v1/activations', 'API key', 'Paginated published activations. Supports since, area, hazard, state, limit, and cursor.'],
  ['GET', '/integration/v1/activations/{id}', 'API key', 'Full decision record with evidence, approvals, trace, and links.'],
  ['GET', '/integration/v1/activations/{id}/cap.xml', 'API key', 'CAP XML for an individual activation.'],
  ['GET', '/integration/v1/activations/{id}/husika-payload.json', 'API key', 'Husika-ingestor-compatible payload; Linda never dispatches it.'],
  ['GET', '/integration/v1/activations/{id}/verify', 'API key', 'Event-chain, signature, and manifest verification report.'],
]

export function DeveloperDocsPage({ embedded = false }: { embedded?: boolean }) {
  const [language, setLanguage] = useState('curl')
  const baseUrl = window.location.origin
  const examples: Record<string, string> = {
    curl: `curl --request GET \\\n  --url ${baseUrl}/integration/v1/activations?state=APPROVED \\\n  --header 'Authorization: Bearer linda_your_api_key'`,
    javascript: `const response = await fetch('${baseUrl}/integration/v1/activations?state=APPROVED', {\n  headers: { Authorization: 'Bearer linda_your_api_key' },\n});\n\nconst { items, next } = await response.json();`,
    python: `import requests\n\nresponse = requests.get(\n    '${baseUrl}/integration/v1/activations',\n    params={'state': 'APPROVED'},\n    headers={'Authorization': 'Bearer linda_your_api_key'},\n    timeout=10,\n)\nactivations = response.json()['items']`,
  }

  const content = (
    <Box sx={{ maxWidth: 1180, mx: 'auto', px: { xs: 2, md: 4 }, py: { xs: 4, md: 7 } }}>
      <Stack spacing={4}>
        <Box>
          <Chip label="Integration API · v1" color="success" sx={{ mb: 1 }} />
          <Typography component="h1" variant="h3" gutterBottom>A verifiable activation API for partner systems.</Typography>
          <Typography color="text.secondary" sx={{ maxWidth: 760 }}>
            Consume approved and revoked activation records through CAP or a versioned REST API. Linda is read-only at this boundary:
            people make decisions inside the workspace; partners receive records they can inspect and independently verify.
          </Typography>
        </Box>

        <Alert severity="info">
          Activation records are published for integration only. CAP documents carry <Box component="code" className="mono">status=Exercise</Box>{' '}
          so a downstream aggregator can never mistake this feed for an accredited operational one, and Linda dispatches nothing itself.
        </Alert>

        <Grid container spacing={2}>
          <Grid size={{ xs: 12, md: 7 }}>
            <Card sx={{ height: '100%' }}>
              <CardHeader title="Quick start" subheader="Create a key in the Admin workspace, then call the activation collection." />
              <CardContent>
                <Stack spacing={2}>
                  <Paper variant="outlined" sx={{ p: 1.5, bgcolor: 'action.hover' }}>
                    <Typography variant="body2">Base URL</Typography>
                    <Stack direction="row" alignItems="center" spacing={0.5}>
                      <Typography className="mono">{baseUrl}</Typography>
                      <CopyButton value={baseUrl} label="Copy base URL" />
                    </Stack>
                  </Paper>
                  <Tabs value={language} onChange={(_, value) => setLanguage(value)}>
                    <Tab value="curl" label="cURL" />
                    <Tab value="javascript" label="JavaScript" />
                    <Tab value="python" label="Python" />
                  </Tabs>
                  <Paper variant="outlined" sx={{ p: 2, position: 'relative', bgcolor: 'grey.900', color: 'common.white' }}>
                    <Typography component="pre" className="mono" sx={{ m: 0, whiteSpace: 'pre-wrap', pr: 6 }}>{examples[language]}</Typography>
                    <Box sx={{ position: 'absolute', top: 8, right: 8, color: 'common.white' }}>
                      <CopyButton value={examples[language]} label="Copy example" />
                    </Box>
                  </Paper>
                  <Typography variant="body2" color="text.secondary">
                    Use the opaque <Box component="code" className="mono">next</Box> cursor from a response to request the next page. A key is
                    shown once and can be revoked by an administrator.
                  </Typography>
                </Stack>
              </CardContent>
            </Card>
          </Grid>

          <Grid size={{ xs: 12, md: 5 }}>
            <Card sx={{ height: '100%' }}>
              <CardHeader title="Authentication and integrity" />
              <CardContent>
                <Stack spacing={2}>
                  <Box>
                    <Typography fontWeight={700}>Bearer API key</Typography>
                    <Typography variant="body2" color="text.secondary">
                      Send <Box component="code" className="mono">Authorization: Bearer &lt;key&gt;</Box> for activation records. Public
                      documentation and the CAP feed require no key.
                    </Typography>
                  </Box>
                  <Box>
                    <Typography fontWeight={700}>Rate limit</Typography>
                    <Typography variant="body2" color="text.secondary">
                      60 requests per minute per key. Keys are stored hashed and can be revoked without changing the contract.
                    </Typography>
                  </Box>
                  <Box>
                    <Typography fontWeight={700}>Verify, do not trust blindly</Typography>
                    <Typography variant="body2" color="text.secondary">
                      Use the verification endpoint to recompute event-chain integrity, signature validity, and the exported manifest hash.
                    </Typography>
                  </Box>
                  <Button component="a" href="/integration/v1/openapi.json" target="_blank" rel="noreferrer" variant="outlined">
                    Open live OpenAPI JSON
                  </Button>
                </Stack>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        <Card>
          <CardHeader title="Endpoint reference" subheader="Stable under /integration/v1/. Breaking changes require a new major version." />
          <CardContent>
            <Stack spacing={1}>
              {ENDPOINTS.map(([method, path, auth, description]) => (
                <Paper key={path} variant="outlined" sx={{ p: 1.5, display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '80px minmax(0, 1fr) 90px' }, gap: 1, alignItems: 'center' }}>
                  <Chip size="small" color="success" label={method} sx={{ width: 'fit-content' }} />
                  <Box sx={{ minWidth: 0 }}>
                    <Typography className="mono" fontWeight={700} sx={{ wordBreak: 'break-all' }}>{path}</Typography>
                    <Typography variant="body2" color="text.secondary">{description}</Typography>
                  </Box>
                  <Chip size="small" label={auth} variant="outlined" sx={{ width: 'fit-content' }} />
                </Paper>
              ))}
            </Stack>
          </CardContent>
        </Card>

        <Grid container spacing={2}>
          <Grid size={{ xs: 12, md: 6 }}>
            <Card sx={{ height: '100%' }}>
              <CardHeader title="Webhooks" subheader="Optional push delivery for approved and revoked activations." />
              <CardContent>
                <Typography variant="body2">
                  Administrators register an HTTPS endpoint and select <Box component="code" className="mono">activation.approved</Box> and/or{' '}
                  <Box component="code" className="mono">activation.revoked</Box>. Each delivery includes{' '}
                  <Box component="code" className="mono">X-Linda-Event</Box>, <Box component="code" className="mono">X-Linda-Delivery</Box>, and a
                  raw-body HMAC in <Box component="code" className="mono">X-Linda-Signature</Box>. The delivery id matches the audit row.
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid size={{ xs: 12, md: 6 }}>
            <Card sx={{ height: '100%' }}>
              <CardHeader title="Useful links" />
              <CardContent>
                <Stack spacing={1}>
                  <Button component="a" href="/cap/feed.xml" target="_blank" rel="noreferrer">Open the public CAP feed</Button>
                  <Button component="a" href="/integration/v1/schemas/activation.json" target="_blank" rel="noreferrer">Open the activation JSON Schema</Button>
                  <Button component="a" href="/integration/v1/docs" target="_blank" rel="noreferrer">Open the server-side API reference</Button>
                </Stack>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </Stack>
    </Box>
  )

  if (embedded) return content
  return (
    <Box minHeight="100dvh" sx={{ bgcolor: 'background.default' }}>
      <Box sx={{ borderBottom: 1, borderColor: 'divider', bgcolor: 'background.paper', px: { xs: 2, md: 5 }, py: 1.5 }}>
        <Stack direction="row" justifyContent="space-between" alignItems="center">
          <Stack direction="row" spacing={1.5} alignItems="center">
            <Logo height={28} />
            <Typography variant="body2" color="text.secondary">Developers</Typography>
          </Stack>
          <Button component={Link} to="/login">Sign in to the workspace</Button>
        </Stack>
      </Box>
      {content}
    </Box>
  )
}

export function IntegrationsPage() {
  return <DeveloperDocsPage embedded />
}
