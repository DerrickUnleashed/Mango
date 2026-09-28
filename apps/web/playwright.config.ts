import { defineConfig, devices } from '@playwright/test'

/**
 * End-to-end tests drive the real application: the FastAPI backend and the
 * Vite dev server, in a real browser. Nothing is stubbed, so a passing run
 * means upload -> process -> render genuinely works together.
 *
 * The dev server is used rather than a production build because it already
 * proxies /api to the backend, which is exactly the arrangement a developer
 * runs locally. The alternative -- building and serving dist -- would add a
 * build step to every run to test the same wiring.
 *
 * `reuseExistingServer` is on locally and off in CI, where a leftover server
 * from a previous job would silently invalidate the run.
 */
const API_PORT = 8001
const WEB_PORT = 5173

export default defineConfig({
  testDir: './e2e',
  // Fail the run rather than pass quietly if a selector stops matching.
  forbidOnly: !!process.env.CI,
  // Retries mask flakiness locally, where a failure is a real signal.
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: process.env.CI ? [['github'], ['list']] : [['list']],
  timeout: 90_000,
  expect: { timeout: 15_000 },

  use: {
    baseURL: `http://localhost:${WEB_PORT}`,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },

  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],

  webServer: [
    {
      // The scratch tree is reset here, inside the command, rather than in a
      // globalSetup hook. Playwright starts webServer *before* globalSetup, so
      // a globalSetup that wiped the directory deleted the SQLite file out
      // from under the already-running API and every job then failed with
      // "no such table: videos". Doing it here makes the ordering explicit:
      // wipe, then start.
      //
      // SQLite will not create the parent directory of its own database, and
      // the API needs its upload and processed directories to exist.
      command:
        'rm -rf /tmp/ov-e2e && ' +
        'mkdir -p /tmp/ov-e2e/uploads /tmp/ov-e2e/processed && ' +
        'uv run --project apps/api uvicorn app.main:app ' +
        '--app-dir apps/api --port 8001 --host 127.0.0.1',
      url: `http://127.0.0.1:${API_PORT}/api/health`,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      cwd: '../..',
      env: {
        DATABASE_URL: 'sqlite:////tmp/ov-e2e/e2e.db',
        UPLOAD_DIR: '/tmp/ov-e2e/uploads',
        PROCESSED_DIR: '/tmp/ov-e2e/processed',
        AUTO_CREATE_TABLES: 'true',
        ENVIRONMENT: 'development',
      },
    },
    {
      command: 'npm run dev',
      url: `http://localhost:${WEB_PORT}`,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      cwd: '.',
    },
  ],
})
