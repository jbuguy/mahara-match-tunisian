import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/candidates': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/employers': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/training-providers': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/auth': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/auth/email': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/api/v1': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/employer-agent': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/health': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/platform': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
