@echo off
rem Stop a running newsalert listener (it has no window while it waits for alerts).
powershell -NoProfile -ExecutionPolicy Bypass -Command "$p = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*newsalert_listener.py*' -and $_.ProcessId -ne $PID }; if ($p) { $p | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }; Write-Host ('Stopped ' + @($p).Count + ' listener process(es).') } else { Write-Host 'No listener is running.' }"
pause
