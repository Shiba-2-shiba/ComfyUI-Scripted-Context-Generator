import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

import type { ComfyPage } from '@e2e/fixtures/ComfyPage'
import {
  comfyPageFixture as test,
  comfyExpect as expect
} from '@e2e/fixtures/ComfyPage'

type WorkflowNode = {
  id: string | number
  type: string
  widgets_values?: unknown
  inputs?: Array<{ name: string; link?: unknown }>
  outputs?: Array<{ name: string; links?: unknown }>
}

type WorkflowJson = {
  nodes: WorkflowNode[]
  links?: Array<[number, ...unknown[]] | { id: number }>
}

const TEST_DIR = path.dirname(fileURLToPath(import.meta.url))
const REPO_ROOT = process.env.VSCG_CUSTOM_NODE_ROOT
  ? path.resolve(process.env.VSCG_CUSTOM_NODE_ROOT)
  : path.resolve(TEST_DIR, '..', '..', '..')
const WORKFLOWS = JSON.parse(
  fs.readFileSync(path.join(REPO_ROOT, 'workflow_samples.json'), 'utf-8')
) as Array<{
  id: string
  path: string
  surface: string
  recommended: boolean
  expected_node_types: string[]
}>

function customWorkflowSnapshot(workflow: WorkflowJson) {
  return workflow.nodes
    .map((node) => ({
      id: String(node.id),
      type: node.type,
      widgets_values: node.widgets_values ?? null,
      inputs: (node.inputs ?? []).map((input) => ({
        name: input.name,
        link: input.link ?? null
      })),
      outputs: (node.outputs ?? []).map((output) => ({
        name: output.name,
        links: output.links ?? null
      }))
    }))
    .sort((a, b) => a.id.localeCompare(b.id))
}

function workflowLinks(workflow: WorkflowJson) {
  return [...(workflow.links ?? [])].sort(
    (a, b) =>
      (Array.isArray(a) ? a[0] : a.id) - (Array.isArray(b) ? b[0] : b.id)
  )
}

async function importWorkflow(
  comfyPage: ComfyPage,
  workflow: (typeof WORKFLOWS)[number]
) {
  const source = JSON.parse(
    fs.readFileSync(path.join(REPO_ROOT, workflow.path), 'utf-8')
  ) as WorkflowJson
  await comfyPage.workflowUploadInput.setInputFiles(
    path.join(REPO_ROOT, workflow.path)
  )
  await expect(comfyPage.workflowUploadInput).toHaveValue('')
  await comfyPage.workflow.waitForWorkflowIdle()
  await expect
    .poll(() => comfyPage.nodeOps.getGraphNodesCount())
    .toBe(source.nodes.length)
  const imported = await comfyPage.workflow.getExportedWorkflow()
  expect(workflowLinks(imported)).toEqual(workflowLinks(source))
  for (const expectedNode of source.nodes) {
    const importedNode = imported.nodes.find(
      (node) => node.id === expectedNode.id
    )
    expect(importedNode?.type).toBe(expectedNode.type)
    if (
      expectedNode.type !== 'PreviewAny' &&
      Array.isArray(expectedNode.widgets_values)
    ) {
      const importedValues = importedNode?.widgets_values
      expect(
        Array.isArray(importedValues) &&
          importedValues.slice(0, expectedNode.widgets_values.length)
      ).toEqual(expectedNode.widgets_values)
    }
  }
  await expect(comfyPage.toast.toastErrors).toHaveCount(0)
  expect(
    await comfyPage.page.evaluate(() =>
      window
        .app!.graph.nodes.filter((node) => node.has_errors)
        .map((node) => node.type)
    )
  ).toEqual([])
  const garnishWidgets = await comfyPage.page.evaluate(() =>
    window
      .app!.graph.nodes.find((node) => node.type === 'ContextGarnish')
      ?.widgets?.map((widget) => ({ name: widget.name, value: widget.value }))
  )
  expect(garnishWidgets).toEqual(
    expect.arrayContaining([
      { name: 'max_items', value: 3 },
      { name: 'emotion_nuance', value: 'random' }
    ])
  )
  return imported
}

test.describe(
  'Custom workflow roundtrip',
  { tag: ['@canvas', '@widget'] },
  () => {
    test.use({
      initialSettings: {
        'Comfy.Workflow.WorkflowTabsPosition': 'Sidebar',
        'Comfy.Workflow.Persist': true
      }
    })

    for (const workflow of WORKFLOWS) {
      test(`${workflow.id} workflow imports all custom nodes, links and widgets`, async ({
        comfyPage
      }) => {
        const imported = await importWorkflow(comfyPage, workflow)
        expect(imported.nodes.map((node) => node.type)).toEqual(
          expect.arrayContaining(workflow.expected_node_types)
        )
      })

      test(`${workflow.id} workflow survives save and reload`, async ({
        comfyPage
      }, testInfo) => {
        const before = await importWorkflow(comfyPage, workflow)
        const saveName = `roundtrip-${workflow.id}-${Date.now()}-${testInfo.workerIndex}`
        await comfyPage.keyboard.ctrlSend('s')
        const saveDialog = comfyPage.menu.topbar.getSaveDialog()
        await saveDialog.fill(saveName)
        await saveDialog.press('Enter')
        await expect(saveDialog).toBeHidden()
        await comfyPage.workflow.waitForWorkflowIdle()

        await comfyPage.command.executeCommand('Comfy.NewBlankWorkflow')
        await expect.poll(() => comfyPage.nodeOps.getGraphNodesCount()).toBe(0)
        await comfyPage.workflow.reloadAndWaitForApp()
        const workflowsTab = comfyPage.menu.workflowsTab
        await workflowsTab.open()
        await workflowsTab.getPersistedItem(saveName).dblclick()
        await comfyPage.workflow.waitForWorkflowIdle()
        await expect
          .poll(async () =>
            (await workflowsTab.getActiveWorkflowName()).replace(/^\*/, '')
          )
          .toBe(saveName)
        const after = await comfyPage.workflow.getExportedWorkflow()
        expect(after.nodes).toHaveLength(before.nodes.length)
        expect(workflowLinks(after)).toEqual(workflowLinks(before))
        expect(customWorkflowSnapshot(after)).toEqual(
          customWorkflowSnapshot(before)
        )
        await expect(comfyPage.toast.toastErrors).toHaveCount(0)
        await testInfo.attach('saved-workflow', {
          body: JSON.stringify(after, null, 2),
          contentType: 'application/json'
        })
        await testInfo.attach('reopened-workflow', {
          body: await comfyPage.page.screenshot(),
          contentType: 'image/png'
        })
      })
    }
  }
)
