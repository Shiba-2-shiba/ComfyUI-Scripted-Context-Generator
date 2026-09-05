param(
  [string]$Python = 'python',
  [int]$Port = 8188,
  [string]$ComfyRoot = $env:VSCG_COMFYUI_ROOT,
  [string]$CustomNodeRoot = '',
  [string]$SourceSentinelPath = '',
  [string]$ActivePluginRoot = '',
  [string]$FrontendRoot = $env:VSCG_FRONTEND_ROOT,
  [string]$FrontendBuildRoot = $env:VSCG_FRONTEND_BUILD_ROOT,
  [string]$TestResultPath = ''
)

$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$activeRoot = if ($ActivePluginRoot) { (Resolve-Path -LiteralPath $ActivePluginRoot).Path } else { $repoRoot }
$sourceRoot = if ($CustomNodeRoot) { (Resolve-Path -LiteralPath $CustomNodeRoot).Path } else { $repoRoot }
if ($CustomNodeRoot -and $sourceRoot -eq $activeRoot) {
  throw '-CustomNodeRoot must name an isolated candidate root, not the active plugin root.'
}
if (-not (Test-Path -LiteralPath (Join-Path $sourceRoot '__init__.py') -PathType Leaf)) {
  throw "Custom node root is incomplete: $sourceRoot"
}
$comfyDir = if ($ComfyRoot) { $ComfyRoot } else { Join-Path $activeRoot 'ComfyUI' }
if (-not (Test-Path -LiteralPath (Join-Path $comfyDir 'main.py') -PathType Leaf)) {
  throw "ComfyUI workspace is missing or incomplete: $comfyDir. Set -ComfyRoot or VSCG_COMFYUI_ROOT to an existing ComfyUI checkout."
}
$comfyDir = (Resolve-Path -LiteralPath $comfyDir).Path
$frontendDir = if ($FrontendRoot) { $FrontendRoot } else { Join-Path $activeRoot 'ComfyUI_frontend' }
if (-not (Test-Path -LiteralPath (Join-Path $frontendDir 'package.json') -PathType Leaf) -or
    -not (Test-Path -LiteralPath (Join-Path $frontendDir 'src') -PathType Container)) {
  throw "Frontend workspace is missing or incomplete: $frontendDir. Set -FrontendRoot or VSCG_FRONTEND_ROOT to an existing ComfyUI_frontend checkout."
}
$frontendDir = (Resolve-Path -LiteralPath $frontendDir).Path
$devtoolsDir = Join-Path $frontendDir 'tools/devtools'
if (-not (Test-Path -LiteralPath (Join-Path $devtoolsDir '__init__.py') -PathType Leaf)) {
  throw "Frontend browser fixture devtools are missing: $devtoolsDir"
}
$frontendRevision = & git -C $frontendDir rev-parse HEAD
if ($LASTEXITCODE -ne 0) { throw "Cannot identify frontend revision: $frontendDir" }
$devtoolsHashes = [ordered]@{}
$devtoolsPending = [Collections.Generic.Stack[string]]::new()
$devtoolsPending.Push($devtoolsDir)
while ($devtoolsPending.Count -gt 0) {
  foreach ($entry in (Get-ChildItem -LiteralPath $devtoolsPending.Pop() -Force | Sort-Object Name)) {
    if ($entry.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "Unexpected devtools junction: $($entry.FullName)" }
    if ($entry.PSIsContainer) {
      if ($entry.Name -ne '__pycache__') { $devtoolsPending.Push($entry.FullName) }
    } elseif ($entry.Extension -notin @('.pyc', '.pyo')) {
      $relative = $entry.FullName.Substring($devtoolsDir.Length).TrimStart('\','/').Replace('\','/')
      $devtoolsHashes[$relative] = (Get-FileHash -LiteralPath $entry.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    }
  }
}
$frontendBuild = if ($FrontendBuildRoot) { $FrontendBuildRoot } else { Join-Path $frontendDir 'dist' }
if (-not (Test-Path -LiteralPath (Join-Path $frontendBuild 'index.html') -PathType Leaf)) {
  throw "Frontend build is missing: $frontendBuild. Build the supplied frontend before running the browser gate."
}
$frontendBuild = (Resolve-Path -LiteralPath $frontendBuild).Path
$playwright = Join-Path $frontendDir 'node_modules/.bin/playwright.cmd'
if (-not (Test-Path -LiteralPath $playwright -PathType Leaf)) {
  throw "Frontend Playwright dependencies are missing: $playwright. Prepare the frontend workspace before running this gate."
}
if ((Test-NetConnection -ComputerName 127.0.0.1 -Port $Port -WarningAction SilentlyContinue).TcpTestSucceeded) {
  throw "Port $Port is already in use. Choose a free -Port so the gate cannot connect to an unrelated backend."
}
$logRoot = Join-Path $activeRoot 'assets/results/browser'
if ($CustomNodeRoot -and ([IO.Path]::GetFullPath($logRoot) + [IO.Path]::DirectorySeparatorChar).StartsWith(
    $sourceRoot.TrimEnd('\','/') + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
  throw 'Browser runtime outputs must be outside the isolated candidate source.'
}
$runStamp = (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [guid]::NewGuid().ToString('N').Substring(0, 8)
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

# Prune before descending: generated trees can be huge or contain source junctions.
$sourceFiles = [Collections.Generic.List[IO.FileInfo]]::new()
$pendingDirectories = [Collections.Generic.Stack[string]]::new()
$pendingDirectories.Push($sourceRoot)
$excludedDirectories = @('.git', '.omx', '__pycache__', 'ComfyUI', 'ComfyUI_frontend', 'node_modules', 'test_logs')
while ($pendingDirectories.Count -gt 0) {
  foreach ($entry in (Get-ChildItem -LiteralPath $pendingDirectories.Pop() -Force)) {
    if ($entry.Attributes -band [IO.FileAttributes]::ReparsePoint) { continue }
    if ($entry.PSIsContainer) {
      $relative = $entry.FullName.Substring($sourceRoot.Length).TrimStart('\','/').Replace('\','/')
      if ($entry.Name -in $excludedDirectories -or $relative -match '(^|/)assets/results$' -or
          $entry.FullName -in @($comfyDir, $frontendDir)) { continue }
      $pendingDirectories.Push($entry.FullName)
    } else {
      $sourceFiles.Add($entry)
    }
  }
}
$sourceHashLines = foreach ($file in ($sourceFiles | Sort-Object FullName)) {
  $relative = $file.FullName.Substring($sourceRoot.Length).TrimStart('\','/').Replace('\','/')
  "$relative`0$((Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant())"
}
$sourceHashBytes = [Text.Encoding]::UTF8.GetBytes(($sourceHashLines -join "`n"))
$sourceHash = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($sourceHashBytes)).ToLowerInvariant()
New-Item -ItemType Directory -Force -Path $runRoot, $userDir, $modelsDir, $modelsCheckpointDir, $outputDir, $tempDir, $customNodesDir | Out-Null
New-Item -ItemType Junction -Path $customNodeLink -Target $sourceRoot | Out-Null
New-Item -ItemType Junction -Path (Join-Path $customNodesDir 'ComfyUI_devtools') -Target $devtoolsDir | Out-Null
$mountedTarget = (Get-Item -LiteralPath $customNodeLink).Target
if ((Resolve-Path -LiteralPath $mountedTarget).Path -ne $sourceRoot) {
  throw 'Candidate custom-node junction target mismatch.'
}
$sentinel = [ordered]@{
  schema_version = 'candidate-custom-node-source-sentinel/v1'
  active_plugin_root = $activeRoot
  loaded_active_plugin = ($sourceRoot -eq $activeRoot)
  loaded_candidate_root = $sourceRoot
  mount_path = $customNodeLink
  source_content_sha256 = $sourceHash
  frontend_build_root = $frontendBuild
  frontend_index_sha256 = (Get-FileHash -LiteralPath (Join-Path $frontendBuild 'index.html') -Algorithm SHA256).Hash.ToLowerInvariant()
  frontend_revision = $frontendRevision
  frontend_devtools_root = $devtoolsDir
  frontend_devtools_sha256 = $devtoolsHashes
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
$previousSourceRoot = $env:VSCG_CUSTOM_NODE_ROOT
$previousJsonOutput = $env:PLAYWRIGHT_JSON_OUTPUT_FILE

try {
  $env:VSCG_CUSTOM_NODE_ROOT = $sourceRoot
  & (Join-Path $PSScriptRoot 'sync_upstream_verification_assets.ps1') -CustomNodeRoot $sourceRoot -FrontendRoot $frontendDir

  $server = Start-Process `
    -FilePath $Python `
    -ArgumentList @(
      'main.py',
      '--multi-user',
      '--cpu',
      '--disable-auto-launch',
      '--front-end-root',
      "`"$frontendBuild`"",
      '--base-directory',
      "`"$runRoot`"",
      '--listen',
      '127.0.0.1',
      '--port',
      "$Port",
      '--user-directory',
      "`"$userDir`"",
      '--output-directory',
      "`"$outputDir`"",
      '--temp-directory',
      "`"$tempDir`""
    ) `
    -WorkingDirectory $comfyDir `
    -RedirectStandardOutput $serverLog `
    -RedirectStandardError $serverErr `
    -WindowStyle Hidden `
    -PassThru

  $ready = $false
  for ($i = 0; $i -lt 45; $i++) {
    if ($server.HasExited) {
      throw "Candidate ComfyUI backend exited before becoming ready. STDERR: $serverErr"
    }
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
  $reporter = 'line'
  if ($TestResultPath) {
    $env:PLAYWRIGHT_JSON_OUTPUT_FILE = [IO.Path]::GetFullPath($TestResultPath)
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $env:PLAYWRIGHT_JSON_OUTPUT_FILE) | Out-Null
    $reporter = 'line,json'
  }

  Push-Location $frontendDir
  try {
    & $playwright test --config playwright.custom-node.config.mts --project chromium "--reporter=$reporter" "--output=$runRoot/playwright"
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
  if ($null -ne $previousSourceRoot) {
    $env:VSCG_CUSTOM_NODE_ROOT = $previousSourceRoot
  } else {
    Remove-Item Env:VSCG_CUSTOM_NODE_ROOT -ErrorAction SilentlyContinue
  }
  if ($null -ne $previousJsonOutput) {
    $env:PLAYWRIGHT_JSON_OUTPUT_FILE = $previousJsonOutput
  } else {
    Remove-Item Env:PLAYWRIGHT_JSON_OUTPUT_FILE -ErrorAction SilentlyContinue
  }
}

Write-Host "Custom workflow GUI round-trip completed. Logs: $runRoot"
