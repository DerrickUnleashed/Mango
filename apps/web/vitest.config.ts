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
  },
})
