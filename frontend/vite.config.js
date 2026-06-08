import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const backendProxyTarget = env.VITE_BACKEND_PROXY_TARGET || process.env.VITE_BACKEND_PROXY_TARGET || 'http://localhost:8000'

  return {
    plugins: [react()],
    appType: 'spa',
    envPrefix: ['VITE_', 'NEXT_PUBLIC_'],
    server: {
      host: '0.0.0.0',  // Bind to all interfaces
      port: 5173,
      strictPort: false,  // Fail if port is occupied
      open: false,       // Don't auto-open browser
      cors: true,
      proxy: {
        '/api': {
          target: backendProxyTarget,
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
  }
})
