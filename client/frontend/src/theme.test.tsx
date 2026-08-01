import { CssBaseline, ThemeProvider } from '@mui/material'
import { renderToString } from 'react-dom/server'
import { describe, expect, it } from 'vitest'

import { themeFor } from './theme'

describe('themeFor', () => {
  it.each(['light', 'dark'] as const)('supplies CssBaseline with a complete %s palette', (mode) => {
    const theme = themeFor(mode)

    expect(theme.palette.mode).toBe(mode)
    expect(theme.palette.background.default).toBeTruthy()
    expect(() => renderToString(<ThemeProvider theme={theme}><CssBaseline /></ThemeProvider>)).not.toThrow()
  })
})
