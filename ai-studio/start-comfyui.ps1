# Starts ComfyUI from wherever setup-comfyui.ps1 installed it, in its own window.
#   powershell -ExecutionPolicy Bypass -File ai-studio\start-comfyui.ps1
$dir = Get-PSDrive -PSProvider FileSystem | ForEach-Object { Join-Path $_.Root 'AI\ComfyUI_windows_portable' } |
  Where-Object { Test-Path (Join-Path $_ 'run_nvidia_gpu.bat') } | Select-Object -First 1
if (-not $dir) { Write-Host 'ComfyUI is not installed yet. Run ai-studio\setup-comfyui.ps1 first.' -ForegroundColor Yellow; exit 1 }
Start-Process -FilePath (Join-Path $dir 'run_nvidia_gpu.bat') -WorkingDirectory $dir
Write-Host "Starting ComfyUI from $dir. It opens http://127.0.0.1:8188 in your browser when ready."
