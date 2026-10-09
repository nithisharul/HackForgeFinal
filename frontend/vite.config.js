import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The dashboard calls /api/...; in dev that is forwarded to the FastAPI server (API_PROXY overrides the default port).
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { '/api': process.env.API_PROXY || 'http://127.0.0.1:8000' } },
})
