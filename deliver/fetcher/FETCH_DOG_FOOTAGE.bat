@echo off
REM ==== Dog story footage fetcher - double-click me ====
REM Re-launch inside "cmd /k" so the window NEVER closes on its own
if /i not "%~1"=="__KEEP__" (
    cmd /k ""%~f0" __KEEP__ %*"
    exit /b
)
setlocal EnableExtensions
chcp 65001 >nul
title Dog Story Footage Fetcher
cd /d "%~dp0"
set "LOG=%~dp0fetch_log.txt"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
REM this variable breaks Python downloads on this PC - remove it for this window
set "SSLKEYLOGFILE="

REM story selection passed on the command line (optional), e.g.  FETCH_DOG_FOOTAGE.bat 7-10
set "SEL=%~2 %~3 %~4 %~5"

echo.>>"%LOG%"
echo ==================== %DATE% %TIME% ====================>>"%LOG%"
echo.
echo  Dog Story Footage Fetcher
echo  Log file: %LOG%
echo.

if not exist "%~dp0fetch_dog_footage.py" (
    echo  ERROR: fetch_dog_footage.py must be in the same folder as this .bat file.
    echo  ERROR: fetch_dog_footage.py missing>>"%LOG%"
    goto :end
)

REM ---------- 1. find or install Python ----------
set "PY="
py -3 -c "import sys; assert sys.version_info>=(3,9)" >nul 2>&1 && set "PY=py -3"
if not defined PY python -c "import sys; assert sys.version_info>=(3,9)" >nul 2>&1 && set "PY=python"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set PY="%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not defined PY (
    echo  Python not found - installing Python 3.12 with winget ^(takes a minute^)...
    echo  installing python via winget>>"%LOG%"
    winget install -e --id Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements >>"%LOG%" 2>&1
)
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set PY="%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not defined PY (
    echo.
    echo  Could not install Python automatically.
    echo  Please install it from https://www.python.org/downloads/  ^(tick "Add python.exe to PATH"^)
    echo  then double-click this file again.
    echo  python install failed>>"%LOG%"
    goto :end
)
echo  Python: %PY%
echo  python=%PY%>>"%LOG%"

REM ---------- 2. private environment + packages (incl. ffmpeg + deno for YouTube) ----------
set "VPY=%~dp0.venv\Scripts\python.exe"
if not exist "%VPY%" (
    echo  Creating private Python environment...
    %PY% -m venv "%~dp0.venv" >>"%LOG%" 2>&1
)
if not exist "%VPY%" (
    echo  ERROR: could not create the Python environment - see fetch_log.txt
    goto :end
)
echo  Installing / updating tools ^(yt-dlp, ffmpeg, deno, image search^)... see log for details
"%VPY%" -m pip install --upgrade pip >>"%LOG%" 2>&1
"%VPY%" -m pip install --upgrade "yt-dlp[default]" requests pillow imageio-ffmpeg ddgs >>"%LOG%" 2>&1
if errorlevel 1 (
    echo  ERROR: package install failed - check your internet connection and fetch_log.txt
    goto :end
)
"%VPY%" -m pip install --upgrade "yt-dlp[curl-cffi]" >>"%LOG%" 2>&1
echo  Installing Whisper speech-to-text ^(uses your NVIDIA GPU^)...
"%VPY%" -m pip install --upgrade faster-whisper nvidia-cublas-cu12 "nvidia-cudnn-cu12==9.*" >>"%LOG%" 2>&1
"%VPY%" -m pip install --upgrade deno >>"%LOG%" 2>&1
if errorlevel 1 (
    echo  deno via pip failed - trying winget ^(YouTube needs a JavaScript runtime^)...
    where deno >nul 2>&1 || winget install -e --id DenoLand.Deno --accept-package-agreements --accept-source-agreements >>"%LOG%" 2>&1
)
echo  Tools ready.
echo.

REM ---------- 3. run the fetcher ----------
"%VPY%" -u "%~dp0fetch_dog_footage.py" %SEL%
echo  python exit code %ERRORLEVEL%>>"%LOG%"

:end
echo.
echo  ------------------------------------------------------------
echo  Finished. This window stays open - scroll up to read, or open fetch_log.txt
echo  Zips to upload are in:  %~dp0DogFootage\_ZIPS_TO_UPLOAD
echo  ------------------------------------------------------------
endlocal
