import { defineConfig, devices } from '@playwright/test';
// RNF06: Chrome/Edge (Chromium), Firefox, Safari (WebKit) and mobile Android/iOS viewports.
// Install once: npx playwright install chromium firefox webkit msedge
export default defineConfig({
  testDir: './tests/browser',
  fullyParallel: false,
  workers: 1,
  use: { baseURL: 'http://127.0.0.1:8787', trace: 'off', screenshot: 'only-on-failure' },
  reporter: 'list',
  timeout: 45000,
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
    { name: 'webkit', use: { ...devices['Desktop Safari'] } },
    { name: 'edge', use: { ...devices['Desktop Edge'], channel: 'msedge' } },
    { name: 'android', use: { ...devices['Pixel 7'] } },
    { name: 'ios', use: { ...devices['iPhone 14'] } },
  ],
});
