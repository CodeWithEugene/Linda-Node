import { FormEvent, ReactNode, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import Alert from '@mui/material/Alert'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Card from '@mui/material/Card'
import CardContent from '@mui/material/CardContent'
import CardHeader from '@mui/material/CardHeader'
import Stack from '@mui/material/Stack'
import TextField from '@mui/material/TextField'
import Typography from '@mui/material/Typography'
import Api from '@mui/icons-material/Api'
import Hub from '@mui/icons-material/Hub'
import VerifiedUser from '@mui/icons-material/VerifiedUser'
import { Logo } from '../Logo'
import { useSession } from '../session'

const capability = (icon: ReactNode, title: string, detail: string) => (
  <Stack key={title} direction="row" spacing={1.5} alignItems="flex-start">
    <Box sx={{ color: 'primary.main', mt: 0.25 }}>{icon}</Box>
    <Box>
      <Typography fontWeight={700}>{title}</Typography>
      <Typography variant="body2" sx={{ color: 'rgba(255,255,255,.78)' }}>{detail}</Typography>
    </Box>
  </Stack>
)

export function LoginPage() {
  const { login } = useSession()
  const navigate = useNavigate()
  const [email, setEmail] = useState('david.drm@demo')
  const [password, setPassword] = useState('linda-demo')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await login(email, password)
      navigate('/')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Sign-in failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Box minHeight="100dvh" sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: 'minmax(0, 1.1fr) minmax(420px, .9fr)' }, bgcolor: 'background.default' }}>
      <Box sx={{ position: 'relative', overflow: 'hidden', px: { xs: 3, sm: 6, lg: 9 }, py: { xs: 5, md: 8 }, display: 'flex', alignItems: 'center', bgcolor: 'primary.dark', color: 'primary.contrastText' }}>
        <Box sx={{ position: 'absolute', width: 420, height: 420, borderRadius: '50%', bgcolor: 'rgba(255,255,255,.06)', top: -160, right: -155 }} />
        <Stack spacing={4} sx={{ position: 'relative', maxWidth: 600 }}>
          <Box>
            <Logo height={44} sx={{ mb: 3 }} />
            <Typography component="h1" variant="h2" sx={{ lineHeight: 1.1, mb: 2 }}>A defensible path from early warning to action.</Typography>
            <Typography variant="body1" sx={{ color: 'rgba(255,255,255,.78)', maxWidth: 540 }}>
              Linda turns evidence into reviewable activation decisions, preserving the policy trace, the role approvals, and every handoff.
            </Typography>
          </Box>
          <Stack spacing={2.25}>
            {capability(<VerifiedUser />, 'Governed decisions', 'Evidence, readiness gates, and three-role approval recorded in a hash-chained audit trail.')}
            {capability(<Hub />, 'Partner-ready handoffs', 'Approved activations export as CAP, a Husika-compatible payload, or a verified offline bundle.')}
            {capability(<Api />, 'A documented integration API', 'A public CAP feed and a versioned REST contract; keys protect activation records.')}
          </Stack>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5} alignItems={{ sm: 'center' }}>
            <Button
              component={Link}
              to="/developers"
              variant="outlined"
              color="inherit"
              startIcon={<Api />}
              sx={{ alignSelf: { xs: 'stretch', sm: 'auto' }, borderColor: 'rgba(255,255,255,.55)', '&:hover': { borderColor: 'common.white', bgcolor: 'rgba(255,255,255,.08)' } }}
            >
              Explore Integration API
            </Button>
            <Typography variant="caption" sx={{ color: 'rgba(255,255,255,.72)' }}>The CAP feed and API documentation are public.</Typography>
          </Stack>
        </Stack>
      </Box>

      <Box sx={{ display: 'grid', placeItems: 'center', px: { xs: 2, sm: 5 }, py: { xs: 4, md: 7 }, bgcolor: 'background.paper' }}>
        <Card elevation={0} sx={{ width: '100%', maxWidth: 440, border: 1, borderColor: 'divider', boxShadow: '0 20px 48px rgba(20, 50, 30, .10)' }}>
          <CardHeader title="Sign in to the workspace" subheader="Auditable activation readiness across the Greater Horn of Africa" />
          <CardContent>
            <Alert severity="info" sx={{ mb: 2 }}>
              Use a fictional demo persona. The password for every account is <strong>linda-demo</strong>.
            </Alert>
            <Stack spacing={1.5} component="form" onSubmit={submit}>
              <TextField autoFocus fullWidth label="Email" value={email} onChange={(event) => setEmail(event.target.value)} />
              <TextField fullWidth label="Password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
              {error && <Alert severity="error">{error}</Alert>}
              <Button type="submit" variant="contained" disabled={busy} sx={{ py: 1 }}>{busy ? 'Signing in…' : 'Sign in'}</Button>
            </Stack>
          </CardContent>
          <CardContent sx={{ pt: 0 }}>
            <Typography variant="caption" color="text.secondary">
              Try Amina (EWS), David (County DRM), Grace (NGO &amp; Finance), observer@demo, or admin@demo.
            </Typography>
          </CardContent>
        </Card>
      </Box>
    </Box>
  )
}
