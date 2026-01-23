import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  appType: 'spa',
  server: {
    host: '0.0.0.0',  // Bind to all interfaces
    port: 5173,
    strictPort: false,  // Fail if port is occupied
    open: false,       // Don't auto-open browser
    cors: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false
      },
    },
  },
  preview: {
    host: '0.0.0.0',
    port: 5173,
    strictPort: true
  }
}) 
