param(
  [string]$Python = 'python',
  [int]$Port = 8188,
  [string]$ComfyRoot = '',
  [string]$CustomNodeRoot = '',
  [string]$SourceSentinelPath = ''
)

$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$sourceRoot = if ($CustomNodeRoot) { (Resolve-Path -LiteralPath $CustomNodeRoot).Path } else { $repoRoot }
if ($CustomNodeRoot -and $sourceRoot -eq $repoRoot) {
  throw '-CustomNodeRoot must name an isolated candidate root, not the active plugin root.'
}
if (-not (Test-Path -LiteralPath (Join-Path $sourceRoot '__init__.py') -PathType Leaf)) {
  throw "Custom node root is incomplete: $sourceRoot"
}
$comfyDir = if ($ComfyRoot) { (Resolve-Path -LiteralPath $ComfyRoot).Path } else { Join-Path $repoRoot 'ComfyUI' }
$frontendDir = Join-Path $repoRoot 'ComfyUI_frontend'
$logRoot = Join-Path $repoRoot 'test_logs'
$runStamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$runRoot = Join-Path $logRoot "custom-workflow-roundtrip-$runStamp"
$serverLog = Join-Path $runRoot 'comfyui.log'
$serverErr = Join-Path $runRoot 'comfyui.err.log'
$userDir = Join-Path $runRoot 'user'
$modelsDir = Join-Path $runRoot 'models'
$modelsCheckpointDir = Join-Path $modelsDir 'checkpoints'
$outputDir = Join-Path $runRoot 'output'
$tempDir = Join-Path $runRoot 'temp'
$customNodesDir = Join-Path $runRoot 'custom_nodes'
$customNodeLink = Join-Path $customNodesDir 'ComfyUI-Scripted-Context-Generator'

New-Item -ItemType Directory -Force -Path $runRoot, $userDir, $modelsDir, $modelsCheckpointDir, $outputDir, $tempDir, $customNodesDir | Out-Null
New-Item -ItemType Junction -Path $customNodeLink -Target $sourceRoot | Out-Null

$sourceFiles = Get-ChildItem -LiteralPath $sourceRoot -File -Recurse | Where-Object {
  $_.FullName -notmatch '[\\/](\.git|\.omx|__pycache__|assets[\\/]results)[\\/]'
} | Sort-Object FullName
$sourceHashLines = foreach ($file in $sourceFiles) {
  $relative = $file.FullName.Substring($sourceRoot.Length).TrimStart('\','/').Replace('\','/')
  "$relative`0$((Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant())"
}
$sourceHashBytes = [Text.Encoding]::UTF8.GetBytes(($sourceHashLines -join "`n"))
$sourceHash = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($sourceHashBytes)).ToLowerInvariant()
$mountedTarget = (Get-Item -LiteralPath $customNodeLink).Target
if ((Resolve-Path -LiteralPath $mountedTarget).Path -ne $sourceRoot) {
  throw 'Candidate custom-node junction target mismatch.'
}
$sentinel = [ordered]@{
  schema_version = 'candidate-custom-node-source-sentinel/v1'
  active_plugin_root = $repoRoot
  loaded_active_plugin = $false
  loaded_candidate_root = $sourceRoot
  mount_path = $customNodeLink
  source_content_sha256 = $sourceHash
}
$sentinelJson = $sentinel | ConvertTo-Json -Compress
$sentinel.sentinel_sha256 = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([Text.Encoding]::UTF8.GetBytes($sentinelJson))).ToLowerInvariant()
if ($SourceSentinelPath) {
  $sentinel | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $SourceSentinelPath -Encoding utf8
}

$server = $null
$previousPlaywrightUrl = $env:PLAYWRIGHT_TEST_URL
$hadTestComfyDir = Test-Path Env:TEST_COMFYUI_DIR
$previousTestComfyDir = $env:TEST_COMFYUI_DIR

try {
  & (Join-Path $PSScriptRoot 'sync_upstream_verification_assets.ps1')

  $server = Start-Process `
    -FilePath $Python `
    -ArgumentList @(
      'main.py',
      '--multi-user',
      '--cpu',
      '--disable-auto-launch',
      '--base-directory',
      $runRoot,
      '--listen',
      '127.0.0.1',
      '--port',
      "$Port",
      '--user-directory',
      $userDir,
      '--output-directory',
      $outputDir,
      '--temp-directory',
      $tempDir
    ) `
    -WorkingDirectory $comfyDir `
    -RedirectStandardOutput $serverLog `
    -RedirectStandardError $serverErr `
    -PassThru

  $ready = $false
  for ($i = 0; $i -lt 45; $i++) {
    if ((Test-NetConnection -ComputerName 127.0.0.1 -Port $Port -WarningAction SilentlyContinue).TcpTestSucceeded) {
      $ready = $true
      break
    }
    Start-Sleep -Seconds 2
  }

  if (-not $ready) {
    throw "ComfyUI backend did not become ready on port $Port.`nSTDERR:`n$(Get-Content $serverErr -Tail 200 | Out-String)"
  }

  $env:PLAYWRIGHT_TEST_URL = "http://127.0.0.1:$Port"
  $env:TEST_COMFYUI_DIR = $runRoot

  Push-Location $frontendDir
  try {
    $playwright = Join-Path $frontendDir 'node_modules/.bin/playwright.cmd'
    & $playwright test --config playwright.custom-node.config.mts --project chromium --reporter=line
    if ($LASTEXITCODE -ne 0) {
      exit $LASTEXITCODE
    }
  } finally {
    Pop-Location
  }
} finally {
  if ($server -and (Get-Process -Id $server.Id -ErrorAction SilentlyContinue)) {
    Stop-Process -Id $server.Id -Force
  }

  if ($null -ne $previousPlaywrightUrl) {
    $env:PLAYWRIGHT_TEST_URL = $previousPlaywrightUrl
  } else {
    Remove-Item Env:PLAYWRIGHT_TEST_URL -ErrorAction SilentlyContinue
  }

  if ($hadTestComfyDir) {
    $env:TEST_COMFYUI_DIR = $previousTestComfyDir
  } else {
    Remove-Item Env:TEST_COMFYUI_DIR -ErrorAction SilentlyContinue
  }
}

Write-Host "Custom workflow GUI round-trip completed. Logs: $runRoot"
