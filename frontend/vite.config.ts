/// <reference types="vitest/config" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Port dédié et fixe pour MyNkap : évite le repli automatique de Vite
    // vers un port voisin (5174, 5175...) quand un autre projet occupe déjà
    // 5173 sur la même machine — ce repli silencieux désynchronisait CORS_ORIGINS
    // (backend) et les origines autorisées Google au fil des lancements.
    port: 5175,
    strictPort: true,
  },
  test: {
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    globals: true,
  },
})
