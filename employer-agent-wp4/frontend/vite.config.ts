import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ command }) => ({
  base: command === 'build' ? '/employer-agent/' : '/',
  plugins: [react()],
  build: {
    outDir: '../employer_agent_wp4/static',
    emptyOutDir: true,
  },
  server: {
    proxy: {
      '/employer-agent': 'http://127.0.0.1:8000',
      '/employers': 'http://127.0.0.1:8000',
    },
  },
}));