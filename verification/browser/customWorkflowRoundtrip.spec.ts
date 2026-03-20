import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

import type { APIRequestContext, Page } from '@playwright/test'
import { expect, test } from '@playwright/test'


type WorkflowNode = {
  id: string | number
  type: string
  widgets_values?: unknown
  inputs?: Array<{ name: string; link?: unknown }>
  outputs?: Array<{ name: string; links?: unknown }>
}

type WorkflowJson = {
  nodes: WorkflowNode[]
  links?: unknown
}


const TEST_DIR = path.dirname(fileURLToPath(import.meta.url))
const REPO_ROOT = path.resolve(TEST_DIR, '..', '..', '..')
const WORKFLOWS = JSON.parse(
  fs.readFileSync(path.join(REPO_ROOT, 'workflow_samples.json'), 'utf-8')
) as Array<{
  id: string
  path: string
  surface: string
  recommended: boolean
  expected_node_types: string[]
}>


const CUSTOM_NODE_TYPES = new Set(
  WORKFLOWS.flatMap((workflow) => {
    const raw = JSON.parse(
      fs.readFileSync(path.join(REPO_ROOT, workflow.path), 'utf-8')
    ) as WorkflowJson
    return raw.nodes.map((node) => node.type)
  })
)


function customWorkflowSnapshot(workflow: WorkflowJson) {
  return workflow.nodes
    .filter((node) => CUSTOM_NODE_TYPES.has(node.type))
    .map((node) => ({
      id: String(node.id),
      type: node.type,
      widgets_values: Array.isArray(node.widgets_values)
        ? node.widgets_values
        : node.widgets_values ?? null,
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


async function findUser(request: APIRequestContext, baseUrl: string, username: string) {
  const response = await request.get(`${baseUrl}/api/users`)
  if (response.status() !== 200) {
    throw new Error(`Failed to retrieve users: ${await response.text()}`)
  }
  const payload = await response.json()
  return Object.entries(payload?.users ?? {}).find(([, name]) => name === username)
}


async function ensureUser(request: APIRequestContext, baseUrl: string, username: string) {
  const existing = await findUser(request, baseUrl, username)
  if (existing?.[0]) {
    return existing[0]
  }

  const response = await request.post(`${baseUrl}/api/users`, {
    data: { username }
  })
  if (response.status() !== 200) {
    throw new Error(`Failed to create user: ${await response.text()}`)
  }
  return await response.json()
}


async function setBackendSettings(request: APIRequestContext, baseUrl: string, userId: string) {
  const response = await request.post(`${baseUrl}/api/devtools/set_settings`, {
    data: {
      'Comfy.UseNewMenu': 'Top',
      'Comfy.Workflow.WorkflowTabsPosition': 'Sidebar',
      'Comfy.NodeBadge.NodeIdBadgeMode': 'None',
      'Comfy.NodeBadge.NodeSourceBadgeMode': 'None',
      'Comfy.EnableTooltips': false,
      'Comfy.userId': userId,
      'Comfy.TutorialCompleted': true,
      'Comfy.VersionCompatibility.DisableWarnings': true,
      'Comfy.RightSidePanel.ShowErrorsTab': false
    }
  })
  if (response.status() !== 200) {
    throw new Error(`Failed to setup settings: ${await response.text()}`)
  }
}


async function waitForAppReady(page: Page) {
  await page.waitForFunction(
    () => Boolean(window.app && window.app.extensionManager && window.app.graphToPrompt)
  )
  await page.waitForFunction(() => document.fonts.status === 'loaded')
}


async function setRuntimeSettings(page: Page) {
  await page.evaluate(async () => {
    await window.app!.extensionManager.setting.set('Comfy.UseNewMenu', 'Top')
    await window.app!.extensionManager.setting.set(
      'Comfy.Workflow.WorkflowTabsPosition',
      'Sidebar'
    )
  })
}


async function openWorkflowsTab(page: Page) {
  const selected = page.locator('.workflows-tab-button.side-bar-button-selected')
  if (!(await selected.isVisible())) {
    await page.locator('.workflows-tab-button').click()
  }
  await page.locator('.comfyui-workflows-browse').waitFor({ state: 'visible' })
}


async function openTopbarMenu(page: Page) {
  const menu = page.locator('.comfy-command-menu')
  if (await menu.isVisible()) {
    await page.locator('body').click({ position: { x: 500, y: 300 } })
    await menu.waitFor({ state: 'hidden', timeout: 1000 })
  }
  await page.locator('.comfy-menu-button-wrapper').click()
  await menu.waitFor({ state: 'visible' })
}


async function triggerTopbarCommand(page: Page, pathParts: string[]) {
  await openTopbarMenu(page)
  const topLevel = page.locator(`.p-menubar-item-label:text-is("${pathParts[0]}")`)
  if (pathParts.length === 1) {
    await topLevel.click()
    return
  }
  await topLevel.hover()
  let submenu = page.locator('.p-tieredmenu-submenu:visible').last()
  await submenu.waitFor({ state: 'visible' })
  for (let index = 1; index < pathParts.length; index += 1) {
    const item = submenu.locator(`.p-tieredmenu-item:has-text("${pathParts[index]}")`).first()
    await item.waitFor({ state: 'visible' })
    if (index === pathParts.length - 1) {
      await item.click()
      return
    }
    await item.hover()
    submenu = page.locator('.p-tieredmenu-submenu:visible').last()
    await submenu.waitFor({ state: 'visible' })
  }
}


async function saveWorkflow(page: Page, workflowName: string) {
  await triggerTopbarCommand(page, ['File', 'Save'])
  const input = page.locator('.p-dialog-content input')
  await input.fill(workflowName)
  await page.keyboard.press('Enter')
  await page.waitForFunction(
    () => !(window.app! as any).extensionManager.workflow.isBusy
  )
  await input.waitFor({ state: 'hidden', timeout: 1000 })
}


async function executeCommand(page: Page, commandId: string) {
  await page.evaluate(async (id) => {
    await window.app!.extensionManager.command.execute(id)
  }, commandId)
}


async function getGraphNodeCount(page: Page) {
  return await page.evaluate(() => (window.app as any)?.graph?._nodes?.length ?? 0)
}


async function getExportedWorkflow(page: Page) {
  return await page.evaluate(async () => {
    return (await window.app!.graphToPrompt()).workflow
  }) as WorkflowJson
}


async function getActiveWorkflowName(page: Page) {
  return await page
    .locator('.comfyui-workflows-open .p-tree-node-selected .node-label')
    .innerText()
}


test.describe('Custom workflow roundtrip', () => {
  test.describe.configure({ mode: 'serial' })

  test.beforeEach(async ({ page, request }, testInfo) => {
    const baseUrl = testInfo.project.use.baseURL as string
    const username = `custom-workflow-roundtrip-${testInfo.parallelIndex}`

    await page.route('**/releases**', async (route) => {
      const url = route.request().url()
      if (url.includes('api.comfy.org') || url.includes('stagingapi.comfy.org')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([])
        })
        return
      }
      await route.continue()
    })

    const userId = await ensureUser(request, baseUrl, username)
    await setBackendSettings(request, baseUrl, userId)

    await page.goto(baseUrl)
    await page.evaluate((id) => {
      localStorage.clear()
      sessionStorage.clear()
      localStorage.setItem('Comfy.userId', id)
    }, userId)
    await page.goto(baseUrl)
    await waitForAppReady(page)
    await setRuntimeSettings(page)
    await openWorkflowsTab(page)
  })

  test('keeps the context workflow as the only recommended browser baseline', async () => {
    const recommended = WORKFLOWS.filter((workflow) => workflow.recommended)
    expect(recommended).toHaveLength(1)
    expect(recommended[0]).toMatchObject({ id: 'context', surface: 'primary' })
  })

  for (const workflow of WORKFLOWS) {
    test(`${workflow.id} workflow survives save and reload`, async ({ page }, testInfo) => {
      await page
        .locator('#comfy-file-input')
        .setInputFiles(path.join(REPO_ROOT, workflow.path))

      await expect
        .poll(() => getGraphNodeCount(page), { timeout: 10000 })
        .toBeGreaterThan(0)

      const before = await getExportedWorkflow(page)
      const beforeSnapshot = customWorkflowSnapshot(before)

      expect(beforeSnapshot.length).toBeGreaterThan(0)
      expect(beforeSnapshot.map((node) => node.type)).toEqual(
        expect.arrayContaining(workflow.expected_node_types)
      )

      const saveName = `roundtrip-${workflow.id}-${Date.now()}-${testInfo.workerIndex}`
      await saveWorkflow(page, saveName)

      await executeCommand(page, 'Comfy.NewBlankWorkflow')
      await openWorkflowsTab(page)

      const persistedItem = page.locator('.comfyui-workflows-browse .node-label', {
        hasText: saveName
      })
      await persistedItem.waitFor({ state: 'visible', timeout: 10000 })
      await persistedItem.click()

      await expect
        .poll(() => getActiveWorkflowName(page), { timeout: 10000 })
        .toBe(saveName)

      const after = await getExportedWorkflow(page)
      const afterSnapshot = customWorkflowSnapshot(after)

      expect(after.nodes.length).toBe(before.nodes.length)
      expect(after.links).toEqual(before.links)
      expect(afterSnapshot).toEqual(beforeSnapshot)
    })
  }
})
