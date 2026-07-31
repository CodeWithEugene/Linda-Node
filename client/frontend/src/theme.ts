import { createTheme } from '@mui/material/styles'

export type ThemePreference = 'system' | 'light' | 'dark'

export const themeFor = (mode: 'light' | 'dark') => createTheme({
  palette: { mode, primary: { main: '#1B5E20' }, secondary: { main: '#0D47A1' }, background: mode === 'light' ? { default: '#f6f8f5' } : undefined },
  typography: { fontFamily: 'Roboto, Arial, sans-serif', h1: { fontWeight: 600 }, h2: { fontWeight: 600 }, h3: { fontWeight: 600 }, h4: { fontWeight: 600 }, fontSize: 14 },
  shape: { borderRadius: 10 },
  components: { MuiButton: { defaultProps: { size: 'small' } }, MuiTextField: { defaultProps: { size: 'small' } }, MuiOutlinedInput: { defaultProps: { size: 'small' } } },
})
