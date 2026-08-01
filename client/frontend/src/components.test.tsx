import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { ThemeProvider } from '@mui/material/styles'

import { FreshnessBadge, StageChip, StateChip, freshnessColor, meterColor, money, relativeTime, severityColor, severityRank } from './components'
import { RouteErrorBoundary } from './ErrorBoundary'
import { answerGuideQuestion } from './AssistTools'
import { themeFor } from './theme'

const render = (node: React.ReactNode) => renderToStaticMarkup(<ThemeProvider theme={themeFor('light')}>{node}</ThemeProvider>)

describe('severity scale', () => {
  it('ranks the ICPAC and policy vocabularies on one scale', () => {
    expect(severityRank('severe')).toBeGreaterThan(severityRank('moderate'))
    expect(severityRank('moderate')).toBeGreaterThan(severityRank('low'))
    expect(severityRank(undefined)).toBe(0)
    expect(severityRank('go')).toBe(severityRank('severe'))
  })

  it('maps severity to consistent colours everywhere', () => {
    expect(severityColor('severe')).toBe('error')
    expect(severityColor('set')).toBe('warning')
    expect(severityColor('low')).toBe('info')
    expect(severityColor(undefined)).toBe('default')
  })

  it('never hands LinearProgress an unsupported colour', () => {
    expect(meterColor(undefined)).toBe('primary')
    expect(meterColor('severe')).toBe('error')
  })
})

describe('freshness', () => {
  it('separates live from every non-live label', () => {
    expect(freshnessColor('live')).toBe('success')
    expect(freshnessColor('replay')).toBe('info')
    expect(freshnessColor('stale')).toBe('warning')
    expect(freshnessColor('cached')).toBe('warning')
  })

  it('renders the label as text, not colour alone', () => {
    expect(render(<FreshnessBadge value="replay" />)).toContain('Replay')
    expect(render(<FreshnessBadge value="stale" />)).toContain('Stale')
  })
})

describe('StageChip', () => {
  it('says no activation is recommended when the engine reached no stage', () => {
    const markup = render(<StageChip stage={null} />)
    expect(markup).toContain('No activation recommended')
  })

  it('shows the stage beside its NDMA phase when one was reached', () => {
    const markup = render(<StageChip stage="set" ndmaPhase="Alarm" />)
    expect(markup).toContain('SET')
    expect(markup).toContain('Alarm')
  })
})

describe('StateChip', () => {
  it('pairs colour with readable text for terminal states', () => {
    expect(render(<StateChip state="REVOKED" />)).toContain('REVOKED')
    expect(render(<StateChip state="READY_FOR_REVIEW" />)).toContain('READY FOR REVIEW')
  })
})

describe('formatting', () => {
  it('formats money with a thousands separator', () => {
    expect(money(393120)).toBe('$393,120')
    expect(money(18000, 'KES')).toBe('KES 18,000')
  })

  it('degrades gracefully without a timestamp', () => {
    expect(relativeTime(undefined)).toBe('—')
    expect(relativeTime(new Date().toISOString())).toBe('just now')
  })
})

describe('RouteErrorBoundary', () => {
  // Error boundaries only catch during client rendering, so exercise the
  // boundary's own logic and its rendered output directly.
  it('captures a thrown error into state', () => {
    expect(RouteErrorBoundary.getDerivedStateFromError(new Error('geometry is null')))
      .toEqual({ error: new Error('geometry is null') })
  })

  it('names the failure instead of leaving a blank screen', () => {
    const boundary = new RouteErrorBoundary({ children: null, routeKey: '/signals' })
    boundary.state = { error: new Error('geometry is null') }
    const markup = renderToStaticMarkup(
      <ThemeProvider theme={themeFor('light')}>{boundary.render()}</ThemeProvider>,
    )
    expect(markup).toContain('This screen could not render')
    expect(markup).toContain('geometry is null')
    expect(markup).toContain('Retry')
  })

  it('passes children straight through when nothing has thrown', () => {
    const boundary = new RouteErrorBoundary({ children: <span>content</span>, routeKey: '/' })
    boundary.state = { error: null }
    expect(renderToStaticMarkup(<>{boundary.render()}</>)).toContain('content')
  })
})

describe('Linda Guide', () => {
  it('answers common workspace questions with bounded guidance', () => {
    expect(answerGuideQuestion('How do approvals work?')).toContain('Approvals tab')
    expect(answerGuideQuestion('What data is used?')).toContain('ICPAC')
    expect(answerGuideQuestion('Can you give emergency advice?')).toContain('I can help with')
  })
})
