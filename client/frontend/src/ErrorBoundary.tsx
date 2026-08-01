import { Component, ErrorInfo, ReactNode } from 'react'
import Alert from '@mui/material/Alert'
import AlertTitle from '@mui/material/AlertTitle'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Stack from '@mui/material/Stack'
import Typography from '@mui/material/Typography'

/**
 * A render error anywhere below this point used to unmount the whole tree and
 * leave a white page with no explanation. Catch it, name it, and keep the rest
 * of the workspace reachable.
 */
export class RouteErrorBoundary extends Component<
  { children: ReactNode; routeKey?: string },
  { error: Error | null }
> {
  state: { error: Error | null } = { error: null }

  static getDerivedStateFromError(error: Error) {
    return { error }
  }

  componentDidUpdate(previous: { children: ReactNode; routeKey?: string }) {
    // Navigating away from a broken screen should clear the error.
    if (this.state.error && previous.routeKey !== this.props.routeKey) {
      this.setState({ error: null })
    }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // eslint-disable-next-line no-console
    console.error('[RouteErrorBoundary]', error, info.componentStack)
  }

  render() {
    const { error } = this.state
    if (!error) return this.props.children
    return (
      <Box sx={{ maxWidth: 720 }}>
        <Alert
          severity="error"
          action={
            <Stack direction="row" spacing={1}>
              <Button color="inherit" size="small" onClick={() => this.setState({ error: null })}>Retry</Button>
              <Button color="inherit" size="small" onClick={() => window.location.assign('/')}>Go home</Button>
            </Stack>
          }
        >
          <AlertTitle>This screen could not render</AlertTitle>
          <Typography variant="body2" sx={{ mb: 1 }}>
            The rest of the workspace is unaffected — use the navigation on the left, or retry.
          </Typography>
          <Typography variant="caption" className="mono" sx={{ wordBreak: 'break-word' }}>
            {error.message || String(error)}
          </Typography>
        </Alert>
      </Box>
    )
  }
}
