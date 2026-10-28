# One-time setup for the Blender pipeline on Windows. Run from the repo root in PowerShell:
#   powershell -ExecutionPolicy Bypass -File long-way-home\tools\setup-windows.ps1
# Assumes Git, Blender, FFmpeg, Python 3.12 and Node.js LTS were installed with winget.

$ErrorActionPreference = 'Stop'
function Refresh-Path {
  $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User')
}
function Ok($msg) { Write-Host "  OK  $msg" -ForegroundColor Green }
function Bad($msg) { Write-Host "  !!  $msg" -ForegroundColor Yellow }
Refresh-Path
$root = Resolve-Path (Join-Path $PSScriptRoot '..')

Write-Host "`n1. Blender on PATH"
$blender = Get-ChildItem 'C:\Program Files\Blender Foundation' -Recurse -Filter blender.exe -ErrorAction SilentlyContinue |
  Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $blender) { Bad 'Blender not found. Run: winget install -e --id BlenderFoundation.Blender'; exit 1 }
$dir = $blender.DirectoryName
$userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
if ($userPath -notlike "*$dir*") { [Environment]::SetEnvironmentVariable('Path', "$userPath;$dir", 'User') }
[Environment]::SetEnvironmentVariable('BLENDER_EXE', $blender.FullName, 'User')
Refresh-Path
Ok "$($blender.FullName)"

Write-Host "`n2. Tools"
foreach ($cmd in 'git', 'ffmpeg', 'node', 'npm', 'py') {
  if (Get-Command $cmd -ErrorAction SilentlyContinue) { Ok $cmd } else { Bad "$cmd missing - reinstall it with winget, then open a new PowerShell" }
}

Write-Host "`n3. Python packages for the soundtrack"
py -3.12 -m pip install --upgrade --quiet numpy pillow
Ok 'numpy, pillow'

Write-Host "`n4. Headless browser for the caption/compositing renderer"
Push-Location $root
npm install --silent
npx playwright install chromium
Pop-Location
Ok 'playwright + chromium'

Write-Host "`n5. GPU check (renders a small test image with Cycles)"
& $blender.FullName -b --factory-startup -P (Join-Path $PSScriptRoot 'gpu-check.py')

Write-Host "`nDone. Close this window, open a new PowerShell in the repo folder and run: claude`n"
