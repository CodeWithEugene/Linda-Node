import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  // Port 8000 is commonly occupied by another local service in this workspace.
  // Keep this overrideable for deployments while making the documented local setup reliable.
  const apiOrigin = env.LINDA_API_ORIGIN || 'http://127.0.0.1:8001'

  return {
    plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        // Map libraries are only needed by the two map screens; keeping them in
        // their own chunks holds the initial payload down.
        manualChunks: {
          maplibre: ['maplibre-gl'],
          leaflet: ['leaflet', 'react-leaflet'],
          datagrid: ['@mui/x-data-grid'],
        },
      },
    },
  },
    server: {
      host: '127.0.0.1',
      port: 5173,
      proxy: {
        '/api': apiOrigin,
        '/cap': apiOrigin,
        '/integration': apiOrigin,
      },
    },
  }
})
