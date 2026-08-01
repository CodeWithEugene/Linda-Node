import Box from '@mui/material/Box'
import type { SxProps, Theme } from '@mui/material/styles'

/**
 * The horizontal wordmark. It is dark-on-transparent artwork, so on the deep
 * green app bar it gets a light plate rather than being recoloured — the mark
 * itself is never altered.
 */
export function Logo({ height = 30, plate = false, sx }: { height?: number; plate?: boolean; sx?: SxProps<Theme> }) {
  return (
    <Box
      sx={{
        display: 'inline-flex',
        alignItems: 'center',
        ...(plate
          ? { bgcolor: 'common.white', borderRadius: 1.5, px: 1, py: 0.5, boxShadow: '0 1px 3px rgba(0,0,0,.18)' }
          : {}),
        ...sx,
      }}
    >
      <Box
        component="img"
        src="/logo-horizontal-900.png"
        alt="Linda Node"
        sx={{ height, width: 'auto', display: 'block' }}
      />
    </Box>
  )
}

/** The umbrella mark alone, for tight spaces such as a collapsed drawer. */
export function LogoMark({ size = 32, sx }: { size?: number; sx?: SxProps<Theme> }) {
  return <Box component="img" src="/favicon-192.png" alt="" aria-hidden sx={{ width: size, height: size, display: 'block', ...sx }} />
}
