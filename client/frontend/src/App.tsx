import { lazy, ReactNode, Suspense, useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { BrowserRouter, Link, Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import Alert from '@mui/material/Alert'
import AppBar from '@mui/material/AppBar'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Chip from '@mui/material/Chip'
import CircularProgress from '@mui/material/CircularProgress'
import CssBaseline from '@mui/material/CssBaseline'
import Dialog from '@mui/material/Dialog'
import DialogContent from '@mui/material/DialogContent'
import DialogTitle from '@mui/material/DialogTitle'
import Divider from '@mui/material/Divider'
import Drawer from '@mui/material/Drawer'
import IconButton from '@mui/material/IconButton'
import List from '@mui/material/List'
import ListItemButton from '@mui/material/ListItemButton'
import ListItemIcon from '@mui/material/ListItemIcon'
import ListItemText from '@mui/material/ListItemText'
import Menu from '@mui/material/Menu'
import MenuItem from '@mui/material/MenuItem'
import Snackbar from '@mui/material/Snackbar'
import Stack from '@mui/material/Stack'
import ThemeProvider from '@mui/material/styles/ThemeProvider'
import Toolbar from '@mui/material/Toolbar'
import Tooltip from '@mui/material/Tooltip'
import Typography from '@mui/material/Typography'
import useMediaQuery from '@mui/material/useMediaQuery'
import AccountTree from '@mui/icons-material/AccountTree'
import AdminPanelSettings from '@mui/icons-material/AdminPanelSettings'
import Api from '@mui/icons-material/Api'
import Brightness4 from '@mui/icons-material/Brightness4'
import Brightness7 from '@mui/icons-material/Brightness7'
import DarkMode from '@mui/icons-material/DarkMode'
import FactCheck from '@mui/icons-material/FactCheck'
import HelpOutline from '@mui/icons-material/HelpOutline'
import Inbox from '@mui/icons-material/Inbox'
import LightMode from '@mui/icons-material/LightMode'
import Logout from '@mui/icons-material/Logout'
import MenuIcon from '@mui/icons-material/Menu'
import Policy from '@mui/icons-material/Policy'
import Public from '@mui/icons-material/Public'
import Source from '@mui/icons-material/Source'
import { api } from './api'
import { ProvenanceLegend } from './components'
import { Logo, LogoMark } from './Logo'
import { SessionProvider, useSession } from './session'
import { themeFor, ThemePreference } from './theme'
import type { SourceStatus } from './types'

export { useSession } from './session'
export { EmptyState, ErrorPanel, ProvenanceLegend, RoleLabel, StateChip } from './components'

const AdminPage = lazy(() => import('./pages').then((module) => ({ default: module.AdminPage })))
const AuditPage = lazy(() => import('./pages').then((module) => ({ default: module.AuditPage })))
const CaseDetailPage = lazy(() => import('./pages').then((module) => ({ default: module.CaseDetailPage })))
const CasesPage = lazy(() => import('./pages').then((module) => ({ default: module.CasesPage })))
const DeveloperDocsPage = lazy(() => import('./pages').then((module) => ({ default: module.DeveloperDocsPage })))
const InboxPage = lazy(() => import('./pages').then((module) => ({ default: module.InboxPage })))
const IntegrationsPage = lazy(() => import('./pages').then((module) => ({ default: module.IntegrationsPage })))
const LibraryPage = lazy(() => import('./pages').then((module) => ({ default: module.LibraryPage })))
const LoginPage = lazy(() => import('./pages').then((module) => ({ default: module.LoginPage })))
const RegionalPage = lazy(() => import('./pages').then((module) => ({ default: module.RegionalPage })))
const SourcesPage = lazy(() => import('./pages').then((module) => ({ default: module.SourcesPage })))

export function App() {
  const [preference, setPreference] = useState<ThemePreference>(() => (localStorage.getItem('linda-theme') as ThemePreference) || 'system')
  const prefersDark = useMediaQuery('(prefers-color-scheme: dark)')
  const mode = preference === 'system' ? (prefersDark ? 'dark' : 'light') : preference
  useEffect(() => localStorage.setItem('linda-theme', preference), [preference])
  useEffect(() => { document.getElementById('app-loader')?.remove() }, [])
  return (
    <ThemeProvider theme={themeFor(mode)}>
      <CssBaseline />
      <BrowserRouter>
        <SessionProvider>
          <RouteGate preference={preference} setPreference={setPreference} />
        </SessionProvider>
      </BrowserRouter>
    </ThemeProvider>
  )
}

function RouteGate(props: { preference: ThemePreference; setPreference: (value: ThemePreference) => void }) {
  const { user, loading, connectionError } = useSession()
  if (loading) {
    return <Box minHeight="100vh" display="grid" sx={{ placeItems: 'center' }}><CircularProgress aria-label="Loading session" /></Box>
  }
  if (connectionError) {
    return (
      <Box minHeight="100vh" display="grid" sx={{ placeItems: 'center', p: 3 }}>
        <Alert severity="error" sx={{ maxWidth: 560 }}>The Linda workspace cannot reach its API. {connectionError}</Alert>
      </Box>
    )
  }
  if (!user) {
    return (
      <Suspense fallback={<PageFallback />}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/developers" element={<DeveloperDocsPage />} />
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </Suspense>
    )
  }
  return (
    <Shell {...props}>
      <Suspense fallback={<PageFallback />}>
        <Routes>
          <Route path="/" element={<RegionalPage />} />
          <Route path="/signals" element={<InboxPage />} />
          <Route path="/cases" element={<CasesPage />} />
          <Route path="/cases/:caseId" element={<CaseDetailPage />} />
          <Route path="/audit" element={<AuditPage />} />
          <Route path="/library" element={<LibraryPage />} />
          <Route path="/sources" element={<SourcesPage />} />
          <Route path="/integrations" element={<IntegrationsPage />} />
          <Route path="/developers" element={<DeveloperDocsPage />} />
          <Route path="/admin" element={user.role === 'admin' ? <AdminPage /> : <Navigate to="/" replace />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </Shell>
  )
}

function PageFallback() {
  return <Box minHeight="45vh" display="grid" sx={{ placeItems: 'center' }}><CircularProgress aria-label="Loading page" /></Box>
}

const NAVIGATION = [
  ['/', 'Regional Readiness', <Public key="regional" />],
  ['/signals', 'Signal Inbox', <Inbox key="inbox" />],
  ['/cases', 'Decision Cases', <FactCheck key="cases" />],
  ['/audit', 'Audit Log', <AccountTree key="audit" />],
  ['/library', 'Policy & Actions', <Policy key="library" />],
  ['/sources', 'Sources', <Source key="sources" />],
  ['/integrations', 'API & Partners', <Api key="integrations" />],
] as const

/**
 * Data-mode strip. Cached, stale, and replay evidence is never presented as
 * live, so the banner reports exactly what produced the current snapshots.
 */
function ModeBanner() {
  const { user } = useSession()
  const status = useQuery({ queryKey: ['sources-status'], queryFn: () => api<SourceStatus>('/api/sources/status'), staleTime: 30_000 })
  if (!status.data) return null
  const sources = status.data.sources
  const stale = sources.filter((item) => item.freshness === 'stale')
  const replay = sources.filter((item) => item.freshness === 'replay')
  const invalid = sources.filter((item) => !item.schema_ok)

  // Only surfaced when the data is not what it should be. A healthy live
  // system shows no banner at all.
  if (invalid.length) {
    return (
      <Alert severity="error" sx={{ mb: 2 }}>
        Schema validation failed for {invalid.map((item) => item.adapter).join(', ')}. Those snapshots cannot ground an assessment.
      </Alert>
    )
  }
  if (stale.length) {
    return (
      <Alert severity="warning" sx={{ mb: 2 }}>
        Upstream unreachable for {stale.map((item) => item.adapter).join(', ')} — showing the last cached snapshot, labelled stale.
      </Alert>
    )
  }
  // Replay fixtures are verbatim ICPAC recordings, so only a team-authored
  // escalation step warrants a warning — and only the admin can clear it.
  const synthetic = sources.filter((item) => item.meta?.synthetic || item.meta?.provenance?.synthetic)
  if (synthetic.length) {
    return (
      <Alert
        severity="warning"
        sx={{ mb: 2 }}
        action={
          user?.role === 'admin' ? (
            <Button color="inherit" size="small" component={Link} to="/admin">Open Admin</Button>
          ) : undefined
        }
      >
        A team-authored escalation (step {status.data.escalation_step}) is driving {synthetic.map((item) => item.adapter).join(', ')} instead
        of the recorded ICPAC statistics.{' '}
        {user?.role === 'admin'
          ? 'Set the escalation step back to 0 under Admin → Evidence source mode.'
          : 'An administrator can reset it to step 0 under Admin → Evidence source mode.'}
      </Alert>
    )
  }
  return null
}

function Shell({ children, preference, setPreference }: { children: ReactNode; preference: ThemePreference; setPreference: (value: ThemePreference) => void }) {
  const { user, logout } = useSession()
  const location = useLocation()
  const navigate = useNavigate()
  const mobile = useMediaQuery((theme) => theme.breakpoints.down('md'))
  const [open, setOpen] = useState(false)
  const [anchor, setAnchor] = useState<HTMLElement | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [helpOpen, setHelpOpen] = useState(false)

  const drawer = (
    <Box role="navigation" sx={{ width: 240, pt: 1 }}>
      <Stack direction="row" spacing={1} alignItems="center" sx={{ px: 2, pb: 1.5, pt: 0.5 }}>
        <LogoMark size={26} />
        <Typography variant="overline" color="text.secondary">Navigation</Typography>
      </Stack>
      <List>
        {NAVIGATION.map(([path, label, icon]) => (
          <ListItemButton key={path} component={Link} to={path} selected={location.pathname === path} onClick={() => setOpen(false)}>
            <ListItemIcon>{icon}</ListItemIcon>
            <ListItemText primary={label} />
          </ListItemButton>
        ))}
        {user?.role === 'admin' && (
          <>
            <Divider sx={{ my: 1 }} />
            <ListItemButton component={Link} to="/admin" selected={location.pathname === '/admin'} onClick={() => setOpen(false)}>
              <ListItemIcon><AdminPanelSettings /></ListItemIcon>
              <ListItemText primary="Admin" />
            </ListItemButton>
          </>
        )}
      </List>
    </Box>
  )

  return (
    <Box display="flex">
      <AppBar position="fixed" color="primary">
        <Toolbar>
          <IconButton color="inherit" onClick={() => setOpen(true)} sx={{ display: { md: 'none' } }} aria-label="Open navigation"><MenuIcon /></IconButton>
          <Box component={Link} to="/" aria-label="Linda Node home" sx={{ display: 'flex', alignItems: 'center', mr: 1 }}>
            <Logo plate height={26} />
          </Box>
          <Box sx={{ flexGrow: 1 }} />
          <Tooltip title="Provenance legend">
            <IconButton color="inherit" onClick={() => setHelpOpen(true)} aria-label="Open provenance legend"><HelpOutline /></IconButton>
          </Tooltip>
          <Tooltip title="Colour theme">
            <IconButton color="inherit" onClick={(event) => setAnchor(event.currentTarget)} aria-label="Change colour theme">
              {preference === 'dark' ? <DarkMode /> : preference === 'light' ? <LightMode /> : <Brightness4 />}
            </IconButton>
          </Tooltip>
          <Chip
            label={user?.role.replaceAll('_', ' ')}
            onClick={() => navigate('/cases')}
            sx={{ ml: 1, bgcolor: 'rgba(255,255,255,.16)', color: 'inherit', display: { xs: 'none', sm: 'inline-flex' } }}
          />
          <IconButton color="inherit" onClick={() => logout().catch(() => setNotice('Could not sign out'))} aria-label="Sign out"><Logout /></IconButton>
        </Toolbar>
      </AppBar>

      <Menu anchorEl={anchor} open={Boolean(anchor)} onClose={() => setAnchor(null)}>
        {(['system', 'light', 'dark'] as ThemePreference[]).map((value) => (
          <MenuItem key={value} selected={preference === value} onClick={() => { setPreference(value); setAnchor(null) }}>
            {value === 'system' ? <Brightness4 fontSize="small" /> : value === 'light' ? <Brightness7 fontSize="small" /> : <DarkMode fontSize="small" />}
            &nbsp;{value === 'system' ? 'System default' : value === 'light' ? 'Light' : 'Dark'}
          </MenuItem>
        ))}
      </Menu>

      <Drawer
        variant={mobile ? 'temporary' : 'permanent'}
        open={mobile ? open : true}
        onClose={() => setOpen(false)}
        sx={{ '& .MuiDrawer-paper': { width: 240, boxSizing: 'border-box', top: mobile ? 0 : 64 } }}
      >
        {drawer}
      </Drawer>

      <Box component="main" sx={{ flexGrow: 1, minWidth: 0, mt: 8, p: { xs: 2, md: 3 }, ml: { md: '240px' } }}>
        <ModeBanner />
        {children}
      </Box>

      <Dialog open={helpOpen} onClose={() => setHelpOpen(false)}>
        <DialogTitle>Provenance legend</DialogTitle>
        <DialogContent>
          <Stack spacing={2}>
            <Typography>
              Every decision trace separates facts taken from an official source, assumptions written into the reviewed policy,
              information a person entered, and advisory AI output.
            </Typography>
            <ProvenanceLegend />
          </Stack>
        </DialogContent>
      </Dialog>

      <Snackbar open={Boolean(notice)} autoHideDuration={5000} onClose={() => setNotice(null)}>
        <Alert severity="error">{notice}</Alert>
      </Snackbar>
    </Box>
  )
}
