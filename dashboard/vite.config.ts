import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/health':   { target: 'http://localhost:8000', changeOrigin: true },
      '/verify':   { target: 'http://localhost:8000', changeOrigin: true },
      '/settings': { target: 'http://localhost:8000', changeOrigin: true },
      // Launcher proxy (separate process on 8001)
      '/launcher': {
        target: 'http://localhost:8001',
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/launcher/, ''),
      },
    },
  },
})
