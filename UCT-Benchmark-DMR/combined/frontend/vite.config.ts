import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import cesium from 'vite-plugin-cesium';
import path from 'path';
import { version } from './package.json';

// https://vitejs.dev/config/
export default defineConfig({
  define: {
    __APP_VERSION__: JSON.stringify(version || 'unknown'),
  },
  plugins: [react(), cesium()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    // Temporarily on for the globe debug session — we need minified stack
    // traces to map back to source lines. Revert after the fix lands.
    sourcemap: true,
    // vite-plugin-cesium already externalises the Cesium runtime (copies
    // Cesium assets + injects the CDN-style worker shims), so we cannot
    // add cesium/resium to manualChunks — Rollup rejects externalised
    // modules. The plugin's own chunk-split handles the lazy-load boundary;
    // any React.lazy(() => import('./OrbitViewer')) call site gets the
    // Cesium deps loaded in its own async chunk via the dynamic import graph.
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    exclude: ['e2e/**', 'node_modules/**'],
  },
});
