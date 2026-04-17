import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import cesium from 'vite-plugin-cesium';
import path from 'path';
import { version } from './package.json';

// https://vitejs.dev/config/
export default defineConfig({
  define: {
    __APP_VERSION__: JSON.stringify(version || 'unknown'),
    // TEMPORARY: force React dev build + full sourcemaps for ONE deploy
    // so we can read the real component stack for the Cesium-globe React
    // error #31 that collapses every page to the SVG fallback. Revert
    // immediately after the fix lands; dev React is 2x size and spammy.
    'process.env.NODE_ENV': JSON.stringify('development'),
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
