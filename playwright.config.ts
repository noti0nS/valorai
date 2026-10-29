import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: './tests/browser',
  fullyParallel: false,
  workers: 1,
  use: { baseURL: 'http://127.0.0.1:8787', trace: 'off', screenshot: 'only-on-failure' },
  reporter: 'list',
  timeout: 45000,
});
