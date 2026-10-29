import { defineConfig } from 'astro/config';
import react from '@astrojs/react';

export default defineConfig({
  integrations: [react()],
  output: 'static',
  vite: { server: { proxy: { '/api': 'http://127.0.0.1:8787' } } },
});
