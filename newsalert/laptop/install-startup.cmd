@echo off
rem Start the newsalert listener automatically every time you log in to Windows.
rem Creates "newsalert listener" in your Startup folder (shell:startup).
rem Undo with uninstall-startup.cmd.
setlocal
set "HERE=%~dp0"
set "NA_PY="
for /f "delims=" %%P in ('py -3 -c "import sys;print(sys.executable)" 2^>nul') do set "NA_PY=%%P"
if not defined NA_PY for /f "delims=" %%P in ('python -c "import sys;print(sys.executable)" 2^>nul') do set "NA_PY=%%P"
if not defined NA_PY goto nopython
set "NA_PYW=%NA_PY:python.exe=pythonw.exe%"
if not exist "%NA_PYW%" goto nopython
set "NA_SCRIPT=%HERE%newsalert_listener.py"
set "NA_DIR=%HERE:~0,-1%"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference = 'Stop'; $q = [char]34; $lnk = Join-Path ([Environment]::GetFolderPath('Startup')) 'newsalert listener.lnk'; $s = (New-Object -ComObject WScript.Shell).CreateShortcut($lnk); $s.TargetPath = $env:NA_PYW; $s.Arguments = $q + $env:NA_SCRIPT + $q; $s.WorkingDirectory = $env:NA_DIR; $s.Description = 'newsalert breaking-news listener'; $s.Save(); Write-Host ('Created ' + $lnk)"
if errorlevel 1 (
  echo Could not create the shortcut.
  pause
  exit /b 1
)
echo.
echo Done. The listener will start by itself the next time you log in.
echo To start it right now, double-click run-listener.cmd.
pause
exit /b 0

:nopython
echo Python was not found.
echo Install it from https://www.python.org/downloads/ and tick "Add python.exe to PATH", then run this again.
pause
exit /b 1
