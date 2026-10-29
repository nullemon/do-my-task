# Local AI studio for the Alienware (RTX 4080 12 GB, 64 GB RAM): ComfyUI portable + open models for
# images, image-to-video, motion transfer, character replacement and video object swap.
#
# Run from the repo root in PowerShell:
#   powershell -ExecutionPolicy Bypass -File ai-studio\setup-comfyui.ps1
# Options:
#   -Root D:\AI                      install somewhere else (needs ~200 GB free for the default packs)
#   -Packs image,video,motion,swap   which model packs to download (add ltx for LTX-2.3, ~45 GB more)
# Safe to re-run: finished downloads are skipped and interrupted ones resume.

param(
  [string]$Root = 'C:\AI',
  [string[]]$Packs = @('image', 'video', 'motion', 'swap')
)
$ErrorActionPreference = 'Stop'
function Ok($m) { Write-Host "  OK  $m" -ForegroundColor Green }
function Warn($m) { Write-Host "  !!  $m" -ForegroundColor Yellow }
function Step($m) { Write-Host "`n== $m" -ForegroundColor Cyan }

$here = $PSScriptRoot
$manifest = Get-Content (Join-Path $here 'models.json') -Raw | ConvertFrom-Json
$Packs = $Packs | ForEach-Object { $_ -split ',' } | ForEach-Object { $_.Trim() } | Where-Object { $_ }

Step 'GPU and driver'
$smi = Get-Command nvidia-smi -ErrorAction SilentlyContinue
if ($smi) { nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader; Ok 'NVIDIA driver found' }
else { Warn 'nvidia-smi not found: install the latest NVIDIA Studio driver from the NVIDIA app first'; exit 1 }

Step 'Disk space'
New-Item -ItemType Directory -Force -Path $Root | Out-Null
$drive = (Get-Item $Root).PSDrive
$freeGB = [math]::Round($drive.Free / 1GB)
$needGB = 30 + 45 * $Packs.Count
if ($freeGB -lt $needGB) { Warn "$freeGB GB free on $($drive.Name):, about $needGB GB recommended. Use -Root on a bigger drive or fewer -Packs."; exit 1 }
Ok "$freeGB GB free on $($drive.Name):"

Step '7-Zip'
$sevenZip = 'C:\Program Files\7-Zip\7z.exe'
if (-not (Test-Path $sevenZip)) {
  winget install -e --id 7zip.7zip --accept-source-agreements --accept-package-agreements --silent | Out-Null
}
if (-not (Test-Path $sevenZip)) { Warn '7-Zip did not install; install it from https://7-zip.org and re-run'; exit 1 }
Ok $sevenZip

Step 'ComfyUI (portable, NVIDIA)'
$portable = Join-Path $Root 'ComfyUI_windows_portable'
$comfy = Join-Path $portable 'ComfyUI'
$dl = Join-Path $Root 'downloads'
New-Item -ItemType Directory -Force -Path $dl | Out-Null
if (-not (Test-Path (Join-Path $comfy 'main.py'))) {
  $archive = Join-Path $dl 'ComfyUI_windows_portable_nvidia.7z'
  curl.exe -L --fail --retry 5 -C - -o $archive 'https://github.com/comfyanonymous/ComfyUI/releases/latest/download/ComfyUI_windows_portable_nvidia.7z'
  if ($LASTEXITCODE -ne 0) { Warn 'ComfyUI download failed; re-run to resume'; exit 1 }
  & $sevenZip x $archive "-o$Root" -y | Out-Null
  if ($LASTEXITCODE -ne 0) { Warn 'Extract failed'; exit 1 }
}
Ok $portable

Step "Models: $($Packs -join ', ')"
$headers = @()
if ($env:HF_TOKEN) { $headers = @('-H', "Authorization: Bearer $env:HF_TOKEN") }
$failed = @()
foreach ($p in $Packs) {
  $pack = $manifest.$p
  if (-not $pack) { Warn "unknown pack '$p' (choose from: $($manifest.PSObject.Properties.Name -join ', '))"; continue }
  Write-Host "`n  [$p] $($pack.about)"
  foreach ($m in $pack.models) {
    $dir = Join-Path $comfy ('models\' + $m.dir)
    $dest = Join-Path $dir $m.name
    if (Test-Path $dest) { Ok "$($m.dir)\$($m.name) (already here)"; continue }
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    Write-Host "  ..  $($m.dir)\$($m.name)"
    curl.exe -L --fail --retry 5 --retry-delay 5 -C - @headers -o "$dest.part" $m.url
    if ($LASTEXITCODE -eq 0) { Move-Item -Force "$dest.part" $dest; Ok "$($m.dir)\$($m.name)" }
    else { Warn "failed: $($m.url)"; $failed += $m.url }
  }
}

Step 'Done'
if ($failed.Count) {
  Warn "$($failed.Count) download(s) failed. Re-run the same command to resume."
  Warn 'If a file says 401/403, open its Hugging Face page, accept the license, then set HF_TOKEN and re-run.'
}
Write-Host "Start ComfyUI:  $portable\run_nvidia_gpu.bat"
Write-Host 'Then open http://127.0.0.1:8188 -> Workflow -> Browse Templates, and pick one of:'
foreach ($p in $Packs) { if ($manifest.$p) { Write-Host "  $($manifest.$p.templates -join ', ')" } }
