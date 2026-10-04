import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  // One .env for the whole module, the same file the backend reads.
  envDir: '..',
  plugins: [react(), tailwindcss()],
  server: {
    // The backend's CORS policy names this exact origin: fail loudly rather than drift.
    port: 5174,
    strictPort: true,
  },
})