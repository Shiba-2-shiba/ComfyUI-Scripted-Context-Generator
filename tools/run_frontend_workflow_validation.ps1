param(
  [string]$CustomNodeRoot = '',
  [string]$SourceSentinelPath = ''
)

$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$sourceRoot = if ($CustomNodeRoot) { (Resolve-Path -LiteralPath $CustomNodeRoot).Path } else { $repoRoot }
if ($CustomNodeRoot -and $sourceRoot -eq $repoRoot) {
  throw '-CustomNodeRoot must name an isolated candidate root, not the active plugin root.'
}
if (-not (Test-Path -LiteralPath (Join-Path $sourceRoot 'workflow_samples.json') -PathType Leaf)) {
  throw "Candidate frontend source is incomplete: $sourceRoot"
}
$frontendDir = Join-Path $repoRoot 'ComfyUI_frontend'

$boundFiles = @('workflow_samples.json') + ((Get-Content -LiteralPath (Join-Path $sourceRoot 'workflow_samples.json') -Raw | ConvertFrom-Json).path)
$hashLines = foreach ($relative in ($boundFiles | Sort-Object -Unique)) {
  $path = Join-Path $sourceRoot $relative
  if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Missing candidate frontend source: $relative" }
  "$relative`0$((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant())"
}
$sourceHash = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([Text.Encoding]::UTF8.GetBytes(($hashLines -join "`n")))).ToLowerInvariant()
$sentinel = [ordered]@{
  schema_version = 'candidate-frontend-source-sentinel/v1'
  active_plugin_root = $repoRoot
  loaded_active_plugin = $false
  loaded_candidate_root = $sourceRoot
  source_content_sha256 = $sourceHash
}
$sentinelJson = $sentinel | ConvertTo-Json -Compress
$sentinel.sentinel_sha256 = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([Text.Encoding]::UTF8.GetBytes($sentinelJson))).ToLowerInvariant()
if ($SourceSentinelPath) {
  $sentinel | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $SourceSentinelPath -Encoding utf8
}
$previousSourceRoot = $env:VSCG_CUSTOM_NODE_ROOT
$env:VSCG_CUSTOM_NODE_ROOT = $sourceRoot

& (Join-Path $PSScriptRoot 'sync_upstream_verification_assets.ps1')

Push-Location $frontendDir
try {
  corepack pnpm exec vitest run --config vitest.custom-node.config.mts
  if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
  }
} finally {
  Pop-Location
  if ($null -ne $previousSourceRoot) {
    $env:VSCG_CUSTOM_NODE_ROOT = $previousSourceRoot
  } else {
    Remove-Item Env:VSCG_CUSTOM_NODE_ROOT -ErrorAction SilentlyContinue
  }
}
