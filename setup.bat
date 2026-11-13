@echo off
rem One-time setup for the dog video pipeline (Windows). Window stays open; log in setup_log.txt
if /i not "%~1"=="run" ( cmd /k ""%~f0" run" & exit /b )
cd /d "%~dp0"
set "SSLKEYLOGFILE="
set "LOG=%~dp0setup_log.txt"
set "PY="
py -3 -c "import sys; assert sys.version_info>=(3,10)" >nul 2>nul && set "PY=py -3"
if not defined PY python -c "import sys; assert sys.version_info>=(3,10)" >nul 2>nul && set "PY=python"
if not defined PY (
  echo Python not found - installing Python 3.12 with winget...
  winget install -e --id Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements
  if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set PY="%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
)
if not defined PY ( echo Install Python from https://www.python.org/downloads/ ^(tick "Add python.exe to PATH"^), then run this again. & goto :eof )
echo [1/5] Python packages (see setup_log.txt)...
%PY% -m pip install -U pip >>"%LOG%" 2>&1
%PY% -m pip install -U kokoro-onnx soundfile numpy pillow opencv-python "yt-dlp[default,curl-cffi]" deno requests imageio-ffmpeg ddgs faster-whisper >>"%LOG%" 2>&1
echo [2/5] NVIDIA libraries for whisper on the GPU (RTX 3060/4060)...
%PY% -m pip install -U nvidia-cublas-cu12 "nvidia-cudnn-cu12==9.*" >>"%LOG%" 2>&1
echo [3/5] ffmpeg...
where ffmpeg >nul 2>nul || winget install -e --id Gyan.FFmpeg --accept-package-agreements --accept-source-agreements
echo [4/5] Kokoro voice model (about 340 MB)...
if not exist models mkdir models
if not exist models\kokoro-v1.0.onnx curl -L -o models\kokoro-v1.0.onnx https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
if not exist models\voices-v1.0.bin curl -L -o models\voices-v1.0.bin https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
echo [5/5] Node.js for maps (optional)...
where node >nul 2>nul || winget install -e --id OpenJS.NodeJS.LTS --accept-package-agreements --accept-source-agreements
where npm >nul 2>nul && ( pushd lib\maps & call npm i d3-geo topojson-client world-atlas >>"%LOG%" 2>&1 & popd )
echo.
echo Done. Next: voice.bat, preview.bat, render.bat, qc.bat (each asks for the story code, e.g. hachiko).
echo (If ffmpeg/node were just installed, close and reopen Claude Code so it sees them.)
