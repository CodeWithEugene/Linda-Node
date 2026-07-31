import { describe, expect, it } from 'vitest'

import { themeFor } from './theme'

describe('themeFor', () => {
  it('creates a palette-mode theme without the incompatible colorSchemes shape', () => {
    const theme = themeFor('light')

    expect(theme.palette.mode).toBe('light')
    expect(theme.palette.background.default).toBe('#f6f8f5')
    expect('colorSchemes' in theme).toBe(false)
  })
})
