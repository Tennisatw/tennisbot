import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

export default defineConfig({
  plugins: [
    svelte({
      compilerOptions: {
        compatibility: { componentApi: 4 },
      },
    }),
  ],
  server: {
    host: '127.0.0.1',
    port: 5173,
  },
});
