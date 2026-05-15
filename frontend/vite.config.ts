import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  base: 'https://arnold.dream.ddns-ip.net/absproxy/5172/',
  server: {
    port: 5172,
    strictPort: true,
    allowedHosts: ["arnold.dream.ddns-ip.net"],
    watch: { usePolling: true, interval: 1000 },
  },
  preview: { port: 4172 },
})
