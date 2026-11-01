# Local AI studio for the Alienware: ComfyUI portable + open models for images, image-to-video,
# motion transfer, character replacement and video object swap.
#
# Run from the repo root in PowerShell:
#   powershell -ExecutionPolicy Bypass -File ai-studio\setup-comfyui.ps1
# It picks the drive with the most free space and the model packs that suit your graphics card.
# Options:
#   -Root D:\AI                 install to a specific folder
#   -Packs image,video_light    choose packs yourself: image, video_light, video, motion, swap, ltx
# Safe to re-run: finished downloads are skipped and interrupted ones resume.

param(
  [string]$Root = '',
  [string[]]$Packs = @()
)
$ErrorActionPreference = 'Stop'
function Ok($m) { Write-Host "  OK  $m" -ForegroundColor Green }
function Warn($m) { Write-Host "  !!  $m" -ForegroundColor Yellow }
function Step($m) { Write-Host "`n== $m" -ForegroundColor Cyan }

$here = $PSScriptRoot
$manifest = Get-Content (Join-Path $here 'models.json') -Raw | ConvertFrom-Json

Step 'GPU, driver and memory'
if (-not (Get-Command nvidia-smi -ErrorAction SilentlyContinue)) { Warn 'nvidia-smi not found: install the latest NVIDIA Studio driver from the NVIDIA app first'; exit 1 }
$gpu = (nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader,nounits | Select-Object -First 1).Split(',') | ForEach-Object { $_.Trim() }
$vramGB = [math]::Round([double]$gpu[2] / 1024)
$ramGB = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB)
Ok "$($gpu[0]), driver $($gpu[1]), $vramGB GB graphics memory, $ramGB GB system RAM"
if (-not $Packs) {
  if ($vramGB -ge 12 -and $ramGB -ge 32) { $Packs = @('image', 'video', 'motion', 'swap') }
  elseif ($ramGB -ge 32) { $Packs = @('image', 'video_light', 'motion') }
  else { $Packs = @('image', 'video_light') }
}
$Packs = $Packs | ForEach-Object { $_ -split ',' } | ForEach-Object { $_.Trim() } | Where-Object { $_ }
Ok "packs: $($Packs -join ', ')"
if ($vramGB -lt 12) { Warn 'Under 12 GB of graphics memory: big video models run, but slowly, by borrowing system RAM.' }
if ($ramGB -lt 32 -and ($Packs -contains 'motion' -or $Packs -contains 'video' -or $Packs -contains 'swap')) {
  Warn 'The 14B video models (video, motion, swap) need 32 GB+ of system RAM on this card; expect failures.'
}

Step 'Disk space'
if (-not $Root) {
  $best = Get-PSDrive -PSProvider FileSystem | Where-Object { $_.Free -gt 0 -and $_.Root -match '^[A-Z]:\\$' } | Sort-Object Free -Descending | Select-Object -First 1
  $Root = Join-Path $best.Root 'AI'
}
New-Item -ItemType Directory -Force -Path $Root | Out-Null
$drive = (Get-Item $Root).PSDrive
$freeGB = [math]::Round($drive.Free / 1GB)
$needGB = 10
foreach ($p in $Packs) { if ($manifest.$p) { $needGB += [int]$manifest.$p.approxGB } }
if ($freeGB -lt $needGB) { Warn "$freeGB GB free on $($drive.Name):, about $needGB GB needed. Use -Root on a bigger drive or fewer -Packs."; exit 1 }
Ok "installing to $Root ($freeGB GB free, about $needGB GB needed)"

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
