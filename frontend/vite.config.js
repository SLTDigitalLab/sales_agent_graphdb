import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // 1. Allow Docker to access the server
    host: true, 
    // 2. Fix Windows Hot Reload by forcing polling
    watch: {
      usePolling: true,
    },
    // Optional: Explicitly set port to match Docker
    port: 5173, 
  },
})