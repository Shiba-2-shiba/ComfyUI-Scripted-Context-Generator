$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$frontendRoot = Join-Path $repoRoot 'ComfyUI_frontend'

$copyMap = @(
  @{
    Source = Join-Path $repoRoot 'verification\frontend\vitest.custom-node.config.mts'
    Destination = Join-Path $frontendRoot 'vitest.custom-node.config.mts'
  },
  @{
    Source = Join-Path $repoRoot 'verification\frontend\customNodeWorkflowCompatibility.test.ts'
    Destination = Join-Path $frontendRoot 'src\platform\workflow\validation\schemas\customNodeWorkflowCompatibility.test.ts'
  },
  @{
    Source = Join-Path $repoRoot 'verification\frontend\customNodeWorkflowRoundtrip.test.ts'
    Destination = Join-Path $frontendRoot 'src\platform\workflow\validation\schemas\customNodeWorkflowRoundtrip.test.ts'
  },
  @{
    Source = Join-Path $repoRoot 'verification\browser\playwright.custom-node.config.mts'
    Destination = Join-Path $frontendRoot 'playwright.custom-node.config.mts'
  },
  @{
    Source = Join-Path $repoRoot 'verification\browser\customWorkflowRoundtrip.spec.ts'
    Destination = Join-Path $frontendRoot 'browser_tests\tests\customWorkflowRoundtrip.spec.ts'
  }
)

foreach ($entry in $copyMap) {
  $destinationDir = Split-Path -Path $entry.Destination -Parent
  New-Item -ItemType Directory -Force -Path $destinationDir | Out-Null
  Copy-Item -Path $entry.Source -Destination $entry.Destination -Force
}

Write-Host "Synced repo-local verification assets into ComfyUI_frontend."
