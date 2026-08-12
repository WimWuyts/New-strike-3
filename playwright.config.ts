import { defineConfig, devices } from '@playwright/test';

/**
 * Draait tegen de gebouwde statische app, niet tegen de dev-server: we willen
 * testen wat er daadwerkelijk uitgeleverd wordt.
 */
export default defineConfig({
  testDir: 'tests/web',
  fullyParallel: true,
  reporter: [['list']],
  use: {
    baseURL: 'http://127.0.0.1:4173',
    trace: 'off',
  },
  webServer: {
    command: 'npx vite preview --port 4173 --strictPort --outDir ../../dist/web',
    url: 'http://127.0.0.1:4173',
    reuseExistingServer: true,
    timeout: 60_000,
  },
  projects: [
    { name: 'desktop', use: { ...devices['Desktop Chrome'] } },
    { name: 'mobile', use: { ...devices['Pixel 7'] } },
  ],
});
