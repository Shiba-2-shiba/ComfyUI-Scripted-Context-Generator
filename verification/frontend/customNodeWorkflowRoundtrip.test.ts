import { createTestingPinia } from '@pinia/testing'
import { setActivePinia } from 'pinia'
import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'
import { beforeEach, describe, expect, it } from 'vitest'

import { LGraph } from '@/lib/litegraph/src/litegraph'
import type { ISerialisedNode, SerialisableGraph } from '@/lib/litegraph/src/types/serialisation'
import {
  type ComfyWorkflowJSON,
  validateComfyWorkflow,
} from '@/platform/workflow/validation/schemas/workflowSchema'


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


function loadWorkflow(workflowPath: string) {
  return JSON.parse(fs.readFileSync(workflowPath, 'utf-8'))
}


function nodeSnapshot(node: ISerialisedNode) {
  return {
    id: node.id,
    type: node.type,
    inputs: (node.inputs ?? []).map((input) => ({
      name: input.name,
      type: input.type,
      link: input.link ?? null,
      slot_index: input.slot_index ?? null,
    })),
    outputs: (node.outputs ?? []).map((output) => ({
      name: output.name,
      type: output.type,
      links: output.links ?? null,
      slot_index: output.slot_index ?? null,
    })),
    widgets_values: node.widgets_values ?? null,
  }
}


function workflowSnapshot(workflow: ComfyWorkflowJSON | SerialisableGraph) {
  const nodes = [...(workflow.nodes ?? [])]
    .sort((a, b) => String(a.id).localeCompare(String(b.id)))
    .map(nodeSnapshot)
  return {
    version: workflow.version,
    nodes,
  }
}


describe('custom node workflow frontend roundtrip', () => {
  beforeEach(() => {
    setActivePinia(createTestingPinia({ stubActions: false }))
  })

  it.each(DEFAULT_WORKFLOWS)(
    'configure -> serialize keeps default baseline $id [$surface] workflow stable',
    async (sample) => {
      const workflowPath = path.join(REPO_ROOT, sample.path)
      const rawWorkflow = loadWorkflow(workflowPath)
      const validatedWorkflow = await validateComfyWorkflow(rawWorkflow)
      expect(validatedWorkflow).not.toBeNull()

      const graph = new LGraph()
      graph.configure(validatedWorkflow as unknown as SerialisableGraph)

      const serialized = graph.serialize() as SerialisableGraph
      const revalidatedWorkflow = await validateComfyWorkflow(serialized)

      expect(revalidatedWorkflow).not.toBeNull()
      expect(workflowSnapshot(serialized)).toEqual(
        workflowSnapshot(validatedWorkflow as ComfyWorkflowJSON)
      )
    }
  )

  it('treats the context workflow as the primary roundtrip baseline', () => {
    const recommended = SAMPLE_WORKFLOWS.filter((sample) => sample.recommended)
    expect(recommended).toHaveLength(1)
    expect(recommended[0].id).toBe('context')
  })
})
