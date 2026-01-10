import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import fs from 'node:fs';

export default defineConfig({
  plugins: [
    svelte({
      compilerOptions: {
        compatibility: { componentApi: 4 },
      },
    }),
  ],
  server: {
    https: {
      key: fs.readFileSync('./10.0.0.31+2-key.pem'),
      cert: fs.readFileSync('./10.0.0.31+2.pem'),
    },
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://127.0.0.1:8000',
        ws: true,
        changeOrigin: true,
      },
    },

    host: '0.0.0.0',
    port: 5173,
  },
});
