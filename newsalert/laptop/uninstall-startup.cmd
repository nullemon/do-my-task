@echo off
rem Stop the newsalert listener from starting at login (removes the Startup shortcut).
powershell -NoProfile -ExecutionPolicy Bypass -Command "$lnk = Join-Path ([Environment]::GetFolderPath('Startup')) 'newsalert listener.lnk'; if (Test-Path $lnk) { Remove-Item $lnk; Write-Host ('Removed ' + $lnk) } else { Write-Host 'No startup shortcut found.' }"
echo If it is running now, double-click stop-listener.cmd to stop it.
pause
