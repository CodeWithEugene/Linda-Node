import { createContext, lazy, ReactNode, Suspense, useContext, useEffect, useMemo, useState } from 'react'
import { Alert, AppBar, Box, Button, Chip, CircularProgress, CssBaseline, Dialog, DialogContent, DialogTitle, Drawer, IconButton, List, ListItemButton, ListItemIcon, ListItemText, Menu, MenuItem, Snackbar, Stack, ThemeProvider, Toolbar, Tooltip, Typography, useMediaQuery } from '@mui/material'
import AccountTree from '@mui/icons-material/AccountTree'
import AdminPanelSettings from '@mui/icons-material/AdminPanelSettings'
import Brightness4 from '@mui/icons-material/Brightness4'
import Brightness7 from '@mui/icons-material/Brightness7'
import DarkMode from '@mui/icons-material/DarkMode'
import FactCheck from '@mui/icons-material/FactCheck'
import Gavel from '@mui/icons-material/Gavel'
import HelpOutline from '@mui/icons-material/HelpOutline'
import LightMode from '@mui/icons-material/LightMode'
import Logout from '@mui/icons-material/Logout'
import MenuIcon from '@mui/icons-material/Menu'
import Policy from '@mui/icons-material/Policy'
import Source from '@mui/icons-material/Source'
import WarningAmber from '@mui/icons-material/WarningAmber'
import { BrowserRouter, Link, Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { api, post, User } from './api'
import { themeFor, ThemePreference } from './theme'

const LoginPage = lazy(() => import('./pages').then((module) => ({ default: module.LoginPage })))
const AdminPage = lazy(() => import('./pages').then((module) => ({ default: module.AdminPage })))
const AuditPage = lazy(() => import('./pages').then((module) => ({ default: module.AuditPage })))
const CaseDetailPage = lazy(() => import('./pages').then((module) => ({ default: module.CaseDetailPage })))
const CasesPage = lazy(() => import('./pages').then((module) => ({ default: module.CasesPage })))
const LibraryPage = lazy(() => import('./pages').then((module) => ({ default: module.LibraryPage })))
const InboxPage = lazy(() => import('./pages').then((module) => ({ default: module.InboxPage })))
const SourcesPage = lazy(() => import('./pages').then((module) => ({ default: module.SourcesPage })))
const PlaceholderPage = lazy(() => import('./pages').then((module) => ({ default: module.PlaceholderPage })))

type Session = { user: User | null; loading: boolean; connectionError: string | null; login: (email: string, password: string) => Promise<void>; logout: () => Promise<void> }
const SessionContext = createContext<Session | null>(null)
export const useSession = () => {
  const value = useContext(SessionContext)
  if (!value) throw new Error('Session context missing')
  return value
}

export function App() {
  const [preference, setPreference] = useState<ThemePreference>(() => (localStorage.getItem('linda-theme') as ThemePreference) || 'system')
  const prefersDark = useMediaQuery('(prefers-color-scheme: dark)')
  const mode = preference === 'system' ? (prefersDark ? 'dark' : 'light') : preference
  useEffect(() => localStorage.setItem('linda-theme', preference), [preference])
  useEffect(() => { document.getElementById('app-loader')?.remove() }, [])
  return <ThemeProvider theme={themeFor(mode)}><CssBaseline /><BrowserRouter><SessionProvider><RouteGate preference={preference} setPreference={setPreference} /></SessionProvider></BrowserRouter></ThemeProvider>
}

function SessionProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null); const [loading, setLoading] = useState(true); const [connectionError, setConnectionError] = useState<string | null>(null)
  useEffect(() => {
    api<User>('/api/me')
      .then(setUser)
      .catch((error) => {
        const message = error instanceof Error ? error.message : 'The Linda API could not be reached.'
        if (!message.includes('Sign in is required') && !message.includes('Request failed (401)')) setConnectionError(message)
        setUser(null)
      })
      .finally(() => setLoading(false))
  }, [])
  const value = useMemo(() => ({ user, loading, connectionError, login: async (email: string, password: string) => setUser(await post<User>('/api/auth/login', { email, password })), logout: async () => { await post<void>('/api/auth/logout'); setUser(null) } }), [user, loading, connectionError])
  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
}

function RouteGate(props: { preference: ThemePreference; setPreference: (value: ThemePreference) => void }) {
  const { user, loading, connectionError } = useSession()
  if (loading) return <Box minHeight="100vh" display="grid" sx={{ placeItems: 'center' }}><CircularProgress aria-label="Loading session" /></Box>
  if (connectionError) return <Box minHeight="100vh" display="grid" sx={{ placeItems: 'center', p: 3 }}><Alert severity="error" sx={{ maxWidth: 560 }}>The Linda workspace cannot reach its API. {connectionError}</Alert></Box>
  if (!user) return <Suspense fallback={<PageFallback />}><Routes><Route path="/login" element={<LoginPage />} /><Route path="*" element={<Navigate to="/login" replace />} /></Routes></Suspense>
  return <Shell {...props}><Suspense fallback={<PageFallback />}><Routes>
    <Route path="/" element={<InboxPage />} />
    <Route path="/cases" element={<CasesPage />} /><Route path="/cases/:caseId" element={<CaseDetailPage />} />
    <Route path="/audit" element={<AuditPage />} /><Route path="/library" element={<LibraryPage />} />
    <Route path="/sources" element={<SourcesPage />} />
    <Route path="/admin" element={user.role === 'admin' ? <AdminPage /> : <Navigate to="/" replace />} />
    <Route path="*" element={<Navigate to="/cases" replace />} />
  </Routes></Suspense></Shell>
}

function PageFallback() { return <Box minHeight="45vh" display="grid" sx={{ placeItems: 'center' }}><CircularProgress aria-label="Loading page" /></Box> }

const navigation = [
  ['/', 'Signal Inbox', <Source />], ['/cases', 'Decision Cases', <FactCheck />], ['/audit', 'Audit Log', <AccountTree />], ['/library', 'Policy & Actions', <Policy />], ['/sources', 'Sources', <Source />],
] as const

function Shell({ children, preference, setPreference }: { children: ReactNode; preference: ThemePreference; setPreference: (value: ThemePreference) => void }) {
  const { user, logout } = useSession(); const location = useLocation(); const navigate = useNavigate(); const mobile = useMediaQuery((theme) => theme.breakpoints.down('md')); const [open, setOpen] = useState(false); const [anchor, setAnchor] = useState<HTMLElement | null>(null); const [notice, setNotice] = useState<string | null>(null); const [helpOpen, setHelpOpen] = useState(false)
  const drawer = <Box role="navigation" sx={{ width: 240, pt: 1 }}><Typography px={2} pb={1} variant="overline" color="text.secondary">Navigation</Typography><List>{navigation.map(([path, label, icon]) => <ListItemButton key={path} component={Link} to={path} selected={location.pathname === path}><ListItemIcon>{icon}</ListItemIcon><ListItemText primary={label} /></ListItemButton>)}{user?.role === 'admin' && <ListItemButton component={Link} to="/admin" selected={location.pathname === '/admin'}><ListItemIcon><AdminPanelSettings /></ListItemIcon><ListItemText primary="Admin" /></ListItemButton>}</List></Box>
  return <Box display="flex"><AppBar position="fixed" color="primary"><Toolbar><IconButton color="inherit" onClick={() => setOpen(true)} sx={{ display: { md: 'none' } }} aria-label="Open navigation"><MenuIcon /></IconButton><Gavel sx={{ mr: 1 }} /><Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>Linda Protocol</Typography><Chip label="Exercise mode" size="small" color="warning" sx={{ mr: 1 }} /><Tooltip title="Provenance legend"><IconButton color="inherit" onClick={() => setHelpOpen(true)} aria-label="Open provenance legend"><HelpOutline /></IconButton></Tooltip><Tooltip title="Theme"><IconButton color="inherit" onClick={(event) => setAnchor(event.currentTarget)} aria-label="Change color theme">{preference === 'dark' ? <DarkMode /> : preference === 'light' ? <LightMode /> : <Brightness4 />}</IconButton></Tooltip><Chip label={user?.role.replaceAll('_', ' ')} onClick={() => navigate('/cases')} sx={{ ml: 1, bgcolor: 'rgba(255,255,255,.16)', color: 'inherit' }} /><IconButton color="inherit" onClick={() => logout().catch(() => setNotice('Could not sign out'))} aria-label="Sign out"><Logout /></IconButton></Toolbar></AppBar>
    <Menu anchorEl={anchor} open={Boolean(anchor)} onClose={() => setAnchor(null)}><MenuItem selected={preference === 'system'} onClick={() => { setPreference('system'); setAnchor(null) }}><Brightness4 fontSize="small" />&nbsp;System default</MenuItem><MenuItem selected={preference === 'light'} onClick={() => { setPreference('light'); setAnchor(null) }}><Brightness7 fontSize="small" />&nbsp;Light</MenuItem><MenuItem selected={preference === 'dark'} onClick={() => { setPreference('dark'); setAnchor(null) }}><DarkMode fontSize="small" />&nbsp;Dark</MenuItem></Menu>
    <Drawer variant={mobile ? 'temporary' : 'permanent'} open={mobile ? open : true} onClose={() => setOpen(false)} sx={{ '& .MuiDrawer-paper': { width: 240, boxSizing: 'border-box', top: mobile ? 0 : 64 } }}>{drawer}</Drawer>
    <Box component="main" sx={{ flexGrow: 1, minWidth: 0, mt: 8, p: { xs: 2, md: 3 }, ml: { md: '240px' } }}><Alert severity="info" icon={<WarningAmber />} sx={{ mb: 2 }}>Demo replay mode may be shown by Person 1 evidence. Every export and partner response is labeled <strong>Exercise</strong>; Linda does not move funds or send public alerts.</Alert>{children}</Box>
    <Dialog open={helpOpen} onClose={() => setHelpOpen(false)}><DialogTitle>Provenance legend</DialogTitle><DialogContent><Typography sx={{ mb: 2 }}>Every decision trace separates source facts from policy assumptions, user-entered information, and advisory AI output.</Typography><ProvenanceLegend /></DialogContent></Dialog>
    <Snackbar open={Boolean(notice)} autoHideDuration={5000} onClose={() => setNotice(null)}><Alert severity="error">{notice}</Alert></Snackbar>
  </Box>
}

export function RoleLabel({ role }: { role: string }) { return role.replaceAll('_', ' ').replace(/\b\w/g, character => character.toUpperCase()) }
export function StateChip({ state }: { state: string }) { const color = state === 'APPROVED' || state === 'RESOLVED' || state === 'HANDED_OFF' ? 'success' : state === 'BLOCKED' || state === 'REVOKED' || state === 'REJECTED' || state === 'DECLINED' ? 'error' : state === 'READY_FOR_REVIEW' || state === 'SET' ? 'warning' : 'default'; return <Chip size="small" label={state.replaceAll('_', ' ')} color={color} /> }
export function ErrorPanel({ error, retry }: { error: unknown; retry?: () => void }) { return <Alert severity="error" action={retry ? <Button color="inherit" size="small" onClick={retry}>Retry</Button> : undefined}>{error instanceof Error ? error.message : 'Something went wrong.'}</Alert> }
export function EmptyState({ children }: { children: ReactNode }) { return <Box sx={{ py: 6, textAlign: 'center', color: 'text.secondary' }}>{children}</Box> }
export function ProvenanceLegend() { return <Stack direction="row" spacing={1} flexWrap="wrap"><Chip size="small" color="success" label="Official source" /><Chip size="small" color="warning" label="Policy assumption" /><Chip size="small" color="info" label="User entered" /><Chip size="small" variant="outlined" label="Dashed = AI output" /></Stack> }
