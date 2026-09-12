param(
  [string]$CustomNodeRoot = '',
  [string]$FrontendRoot = $env:VSCG_FRONTEND_ROOT
)

$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$sourceRoot = if ($CustomNodeRoot) { (Resolve-Path -LiteralPath $CustomNodeRoot).Path } else { $repoRoot }
$frontendDir = if ($FrontendRoot) { $FrontendRoot } else { Join-Path $repoRoot 'ComfyUI_frontend' }
if (-not (Test-Path -LiteralPath (Join-Path $frontendDir 'package.json') -PathType Leaf) -or
    -not (Test-Path -LiteralPath (Join-Path $frontendDir 'src') -PathType Container)) {
  throw "Frontend workspace is missing or incomplete: $frontendDir. Set -FrontendRoot or VSCG_FRONTEND_ROOT to an existing ComfyUI_frontend checkout."
}
$frontendDir = (Resolve-Path -LiteralPath $frontendDir).Path

$copyMap = @(
  @{
    Source = Join-Path $sourceRoot 'verification\frontend\vitest.custom-node.config.mts'
    Destination = Join-Path $frontendDir 'vitest.custom-node.config.mts'
  },
  @{
    Source = Join-Path $sourceRoot 'verification\frontend\customNodeWorkflowCompatibility.test.ts'
    Destination = Join-Path $frontendDir 'src\platform\workflow\validation\schemas\customNodeWorkflowCompatibility.test.ts'
  },
  @{
    Source = Join-Path $sourceRoot 'verification\frontend\customNodeWorkflowRoundtrip.test.ts'
    Destination = Join-Path $frontendDir 'src\platform\workflow\validation\schemas\customNodeWorkflowRoundtrip.test.ts'
  },
  @{
    Source = Join-Path $sourceRoot 'verification\browser\playwright.custom-node.config.mts'
    Destination = Join-Path $frontendDir 'playwright.custom-node.config.mts'
  },
  @{
    Source = Join-Path $sourceRoot 'verification\browser\customWorkflowRoundtrip.spec.ts'
    Destination = Join-Path $frontendDir 'browser_tests\tests\customWorkflowRoundtrip.spec.ts'
  }
)

foreach ($entry in $copyMap) {
  if (-not (Test-Path -LiteralPath $entry.Source -PathType Leaf)) {
    throw "Missing candidate verification asset: $($entry.Source)"
  }
}

foreach ($entry in $copyMap) {
  $destinationDir = Split-Path -Path $entry.Destination -Parent
  New-Item -ItemType Directory -Force -Path $destinationDir | Out-Null
  Copy-Item -LiteralPath $entry.Source -Destination $entry.Destination -Force
}

Write-Host "Synced verification assets from $sourceRoot into $frontendDir."
