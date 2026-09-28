import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
    css: false,
    // Reuse one jsdom environment per worker instead of building one per
    // test file. On CI this was 64% of the suite's tracked time (8.35s of
    // 14.53s), purely environment setup.
    //
    // vmThreads is chosen over the other option Vitest suggests,
    // `isolate: false`, because this keeps per-file isolation. The tests
    // render React components against a shared react-query client and rely
    // on jest-dom globals and explicit cleanup; sharing one module registry
    // across files would make failures depend on execution order. That is
    // not a risk worth a second of CI time, and this is verified with
    // repeated --sequence.shuffle runs rather than assumed.
    pool: 'vmThreads',
    coverage: {
      provider: 'v8',
      reporter: ['text-summary', 'lcov'],
      // Measure every source file, not only those a test happened to import.
      // Without this, adding an untested file looks like no change and the
      // number silently drifts upward on paper only.
      all: true,
      include: ['src/**/*.{ts,tsx}'],
      // Ratchets set just below the current measured values, so ordinary
      // work cannot lower them. Raise as tests are added — the components
      // that are tested are already in the 85–90% range, and the untested
      // api/hooks/layouts layers are what hold the average down.
      thresholds: {
        statements: 30,
        branches: 30,
        functions: 28,
        lines: 30,
      },
    },
  },
})
