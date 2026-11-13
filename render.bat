@echo off
rem Full render in its own window (closing THIS window does not stop it; run again to resume)
if /i not "%~1"=="__KEEP__" ( cmd /k ""%~f0" __KEEP__ %*" & exit /b )
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"
set "SSLKEYLOGFILE="
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
if not exist logs mkdir logs
set "CODE=%~2"
if "%CODE%"=="" set /p CODE=Story code (folder name under cases, e.g. hachiko): 
set "PY=py -3"
%PY% -c "import sys" >nul 2>nul || set "PY=python"
set "LOG=%~dp0logs\render_%CODE%.log"
echo ==== %DATE% %TIME% ==== >>"%LOG%"
start "Dog render %CODE%" cmd /k "set SSLKEYLOGFILE=& set PYTHONUTF8=1& %PY% -u lib\pipeline.py %CODE% render 2>&1 | %PY% -u lib\tee.py "%LOG%""
echo Render started in a separate window. If it stops, run render.bat again: finished scenes are kept.
echo.
echo Finished (exit code %ERRORLEVEL%). Log: %LOG%
echo This window stays open.
endlocal
