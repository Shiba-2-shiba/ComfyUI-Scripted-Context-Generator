$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$frontendDir = Join-Path $repoRoot 'ComfyUI_frontend'

& (Join-Path $PSScriptRoot 'sync_upstream_verification_assets.ps1')

Push-Location $frontendDir
try {
  corepack pnpm exec vitest run --config vitest.custom-node.config.mts
  if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
  }
} finally {
  Pop-Location
}
