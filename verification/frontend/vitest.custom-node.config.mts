import { defineConfig } from 'vitest/config'


export default defineConfig({
  resolve: {
    alias: {
      '@': '/src'
    }
  },
  test: {
    globals: true,
    environment: 'happy-dom',
    setupFiles: ['./vitest.setup.ts'],
    include: [
      'src/platform/workflow/validation/schemas/customNodeWorkflowCompatibility.test.ts',
      'src/platform/workflow/validation/schemas/customNodeWorkflowRoundtrip.test.ts'
    ],
    silent: 'passed-only'
  }
})
