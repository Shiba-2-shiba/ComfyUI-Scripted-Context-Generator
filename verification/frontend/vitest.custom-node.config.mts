import { mergeConfig } from 'vitest/config'

import base from './vite.config.mts'

const config = mergeConfig(base, {
  test: { coverage: { enabled: false }, retry: 0 }
})
config.test.include = [
  'src/platform/workflow/validation/schemas/customNodeWorkflowCompatibility.test.ts',
  'src/platform/workflow/validation/schemas/customNodeWorkflowRoundtrip.test.ts'
]
config.test.setupFiles = ['./vitest.setup.ts']

export default config
