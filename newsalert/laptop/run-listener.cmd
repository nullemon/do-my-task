@echo off
rem Start the newsalert listener in the background (no console window).
rem It writes its log to newsalert_listener.log in this folder.
rem To watch it live instead, run:  python newsalert_listener.py
setlocal
set "HERE=%~dp0"
where pyw >nul 2>nul
if not errorlevel 1 (
  start "" pyw -3 "%HERE%newsalert_listener.py" %*
  goto :eof
)
where pythonw >nul 2>nul
if not errorlevel 1 (
  start "" pythonw "%HERE%newsalert_listener.py" %*
  goto :eof
)
echo Python was not found.
echo Install it from https://www.python.org/downloads/ and tick "Add python.exe to PATH".
pause
