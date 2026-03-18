import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'
import { describe, expect, it } from 'vitest'

import { validateComfyWorkflow } from '@/platform/workflow/validation/schemas/workflowSchema'


const TEST_DIR = path.dirname(fileURLToPath(import.meta.url))
const REPO_ROOT = path.resolve(TEST_DIR, '../../../../../../')
const SAMPLE_WORKFLOWS = JSON.parse(
  fs.readFileSync(path.join(REPO_ROOT, 'workflow_samples.json'), 'utf-8')
) as Array<{
  id: string
  path: string
  surface: string
  recommended: boolean
}>
const DEFAULT_WORKFLOWS = SAMPLE_WORKFLOWS.filter(
  (sample) => sample.surface === 'primary'
)


describe('custom node workflow compatibility', () => {
  it.each(DEFAULT_WORKFLOWS)(
    'frontend schema accepts default baseline $id [$surface]',
    async (sample) => {
      const workflow = JSON.parse(
        fs.readFileSync(path.join(REPO_ROOT, sample.path), 'utf-8')
      )
      await expect(validateComfyWorkflow(workflow)).resolves.not.toBeNull()
    }
  )

  it('keeps the context workflow as the only recommended sample', () => {
    const recommended = SAMPLE_WORKFLOWS.filter((sample) => sample.recommended)
    expect(recommended).toHaveLength(1)
    expect(recommended[0]).toMatchObject({ id: 'context', surface: 'primary' })
  })
})
