import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// The app is served by admin_hub.py at /control (built into ../hub/control).
// `npm run dev` proxies the hub's API to http://localhost:5000 (or HUB_URL).
const hub = process.env.HUB_URL ?? 'http://localhost:5000';
const proxy = Object.fromEntries(['/api', '/photos', '/mapimg'].map((p) => [p, { target: hub, changeOrigin: true }]));

export default defineConfig({
  base: '/control/',
  plugins: [react()],
  server: { port: 5173, proxy },
  build: { outDir: '../hub/control', emptyOutDir: true, chunkSizeWarningLimit: 1500 },
});
