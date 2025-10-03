import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 3000,
    proxy: {
      '/chat': 'http://localhost:8080',
      '/health': 'http://localhost:8080',
      '/feedback': 'http://localhost:8080',
      '/workflow': 'http://localhost:8080',
      '/docs': 'http://localhost:8080',
      '/openapi.json': 'http://localhost:8080'
    }
  },
  build: {
    outDir: 'dist',
    sourcemap: true
  }
})
