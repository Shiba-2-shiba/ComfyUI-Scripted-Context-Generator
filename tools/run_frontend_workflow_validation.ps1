param(
  [string]$CustomNodeRoot = '',
  [string]$SourceSentinelPath = '',
  [string]$ActivePluginRoot = '',
  [string]$FrontendRoot = $env:VSCG_FRONTEND_ROOT,
  [string]$TestResultPath = ''
)

$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$activeRoot = if ($ActivePluginRoot) { (Resolve-Path -LiteralPath $ActivePluginRoot).Path } else { $repoRoot }
$sourceRoot = if ($CustomNodeRoot) { (Resolve-Path -LiteralPath $CustomNodeRoot).Path } else { $repoRoot }
if ($CustomNodeRoot -and $sourceRoot -eq $activeRoot) {
  throw '-CustomNodeRoot must name an isolated candidate root, not the active plugin root.'
}
if (-not (Test-Path -LiteralPath (Join-Path $sourceRoot 'workflow_samples.json') -PathType Leaf)) {
  throw "Candidate frontend source is incomplete: $sourceRoot"
}
$frontendDir = if ($FrontendRoot) { $FrontendRoot } else { Join-Path $activeRoot 'ComfyUI_frontend' }
if (-not (Test-Path -LiteralPath (Join-Path $frontendDir 'package.json') -PathType Leaf) -or
    -not (Test-Path -LiteralPath (Join-Path $frontendDir 'src') -PathType Container)) {
  throw "Frontend workspace is missing or incomplete: $frontendDir. Set -FrontendRoot or VSCG_FRONTEND_ROOT to an existing ComfyUI_frontend checkout."
}
$frontendDir = (Resolve-Path -LiteralPath $frontendDir).Path
$testArguments = @('run', '--config', 'vitest.custom-node.config.mts')
if ($TestResultPath) {
  $resultPath = [IO.Path]::GetFullPath($TestResultPath)
  New-Item -ItemType Directory -Force -Path (Split-Path -Parent $resultPath) | Out-Null
  $testArguments += @('--reporter=default', '--reporter=json', '--outputFile', $resultPath)
}
$vitest = Join-Path $frontendDir $(if ($IsWindows) { 'node_modules/.bin/vitest.cmd' } else { 'node_modules/.bin/vitest' })
if (-not (Test-Path -LiteralPath $vitest -PathType Leaf)) {
  throw "Frontend Vitest dependencies are missing: $vitest. Prepare the frontend workspace before running this gate."
}

$boundFiles = @('workflow_samples.json') + ((Get-Content -LiteralPath (Join-Path $sourceRoot 'workflow_samples.json') -Raw | ConvertFrom-Json).path)
$hashLines = foreach ($relative in ($boundFiles | Sort-Object -Unique)) {
  $path = Join-Path $sourceRoot $relative
  if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Missing candidate frontend source: $relative" }
  "$relative`0$((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant())"
}
$sourceHash = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([Text.Encoding]::UTF8.GetBytes(($hashLines -join "`n")))).ToLowerInvariant()
$sentinel = [ordered]@{
  schema_version = 'candidate-frontend-source-sentinel/v1'
  active_plugin_root = $activeRoot
  loaded_active_plugin = ($sourceRoot -eq $activeRoot)
  loaded_candidate_root = $sourceRoot
  source_content_sha256 = $sourceHash
}
$sentinelJson = $sentinel | ConvertTo-Json -Compress
$sentinel.sentinel_sha256 = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([Text.Encoding]::UTF8.GetBytes($sentinelJson))).ToLowerInvariant()
if ($SourceSentinelPath) {
  $sentinel | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $SourceSentinelPath -Encoding utf8
}
$previousSourceRoot = $env:VSCG_CUSTOM_NODE_ROOT
try {
  $env:VSCG_CUSTOM_NODE_ROOT = $sourceRoot
  & (Join-Path $PSScriptRoot 'sync_upstream_verification_assets.ps1') -CustomNodeRoot $sourceRoot -FrontendRoot $frontendDir
  Push-Location $frontendDir
  try {
    & $vitest @testArguments
    if ($LASTEXITCODE -ne 0) {
      exit $LASTEXITCODE
    }
  } finally {
    Pop-Location
  }
} finally {
  if ($null -ne $previousSourceRoot) {
    $env:VSCG_CUSTOM_NODE_ROOT = $previousSourceRoot
  } else {
    Remove-Item Env:VSCG_CUSTOM_NODE_ROOT -ErrorAction SilentlyContinue
  }
}
