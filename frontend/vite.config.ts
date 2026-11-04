import path from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { '@': path.resolve(import.meta.dirname, './src') },
  },
  server: {
    port: 5173,
    strictPort: true,
    // In development the FastAPI backend runs separately; in production it serves this build.
    // In docker compose the backend is reachable as http://backend:8000.
    proxy: { '/api': process.env.VITE_API_PROXY ?? 'http://localhost:8000' },
    // Bind-mounted sources on macOS/Windows don't emit file events inside containers.
    watch: process.env.VITE_USE_POLLING === 'true' ? { usePolling: true, interval: 300 } : undefined,
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
    rollupOptions: {
      output: {
        // Split only self-contained vendor groups (no imports back into other chunks), so chunk
        // evaluation order can never break. Everything else is left to Rollup's default splitting.
        manualChunks(id) {
          if (/node_modules[\\/](react|react-dom|scheduler)[\\/]/.test(id)) return 'vendor-react'
          if (/node_modules[\\/](zod)[\\/]/.test(id)) return 'vendor-zod'
          return undefined
        },
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    css: false,
  },
})
