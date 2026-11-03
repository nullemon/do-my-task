@echo off
title Andromeda 4K download
cd /d "%~dp0"
echo Downloading the Andromeda 4K master (728 MB, 8 pieces)...
for %%i in (0 1 2 3 4 5 6 7) do (
  echo   piece %%i of 7
  curl -L --fail --retry 3 -o Andromeda-4K.mp4.part%%i "https://github.com/nullemon/do-my-task/raw/claude/kind-maxwell-02hzfk/andromeda-doc/4k-master/Andromeda-4K.mp4.part%%i" || goto :fail
)
echo Joining pieces...
copy /b Andromeda-4K.mp4.part0+Andromeda-4K.mp4.part1+Andromeda-4K.mp4.part2+Andromeda-4K.mp4.part3+Andromeda-4K.mp4.part4+Andromeda-4K.mp4.part5+Andromeda-4K.mp4.part6+Andromeda-4K.mp4.part7 Andromeda-4K.mp4 >nul || goto :fail
echo Checking the file...
certutil -hashfile Andromeda-4K.mp4 SHA256 | find /i "eba7bfb96366e7e28a9a74c1b9b1a903aff27e07c18f99ea8471f97567971099" >nul
if errorlevel 1 (
  echo CHECK FAILED - the file does not match. Run this script again.
  pause
  exit /b 1
)
del Andromeda-4K.mp4.part*
echo.
echo DONE. Andromeda-4K.mp4 is ready in this folder (728 MB, 4K, verified).
pause
exit /b 0
:fail
echo Something went wrong. Check your internet connection and run this script again.
pause
exit /b 1
