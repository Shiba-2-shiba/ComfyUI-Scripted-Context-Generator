param(
  [string]$Python = 'python',
  [int]$Port = 8188
)

$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$comfyDir = Join-Path $repoRoot 'ComfyUI'
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

New-Item -ItemType Directory -Force -Path $runRoot, $userDir, $modelsDir, $modelsCheckpointDir, $outputDir, $tempDir | Out-Null

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
    corepack pnpm exec playwright test --config playwright.custom-node.config.mts --project chromium --reporter=line
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
