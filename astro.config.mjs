import { defineConfig } from 'astro/config';
import react from '@astrojs/react';

const apiUrl = process.env.API_URL || 'http://127.0.0.1:8787';

export default defineConfig({
  integrations: [react()],
  output: 'static',
  vite: {
    server: {
      proxy: {
        '/api': {
          target: apiUrl,
          changeOrigin: true,
          headers: {
            Origin: apiUrl,
          },
        },
      },
    },
  },
});

