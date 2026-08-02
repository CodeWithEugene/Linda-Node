import Box from '@mui/material/Box'
import type { SxProps, Theme } from '@mui/material/styles'

/** The horizontal wordmark uses its transparent artwork directly. */
export function Logo({ height = 30, sx }: { height?: number; sx?: SxProps<Theme> }) {
  return (
    <Box
      sx={{
        display: 'inline-flex',
        alignItems: 'center',
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
