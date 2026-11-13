@echo off
rem Make the narration, captions timing and the audio mix
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
set "LOG=%~dp0logs\voice_%CODE%.log"
echo ==== %DATE% %TIME% ==== >>"%LOG%"
%PY% -u lib\pipeline.py %CODE% voice 2>&1 | %PY% -u lib\tee.py "%LOG%"
echo.
echo Finished (exit code %ERRORLEVEL%). Log: %LOG%
echo This window stays open.
endlocal
