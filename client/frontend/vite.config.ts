import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { '/api': 'http://localhost:8000', '/cap': 'http://localhost:8000', '/integration': 'http://localhost:8000' } },
})
