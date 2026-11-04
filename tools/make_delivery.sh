#!/bin/bash
# Usage: make_delivery.sh <branch> <Title> <Prefix> <1080p.mp4> <4k.mp4>
# Splits both files into 90 MB pieces, writes Get-<Prefix>.bat, pushes to a temporary branch, verifies links.
set -e
BR=$1; TITLE=$2; P=$3; F1=$4; F4=$5
W=/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/$BR
rm -rf $W; mkdir -p $W; cd $W
split -b 90M -d -a 2 "$F1" $P-1080p.mp4.part
split -b 90M -d -a 2 "$F4" $P-4K.mp4.part
n1=$(ls $P-1080p.mp4.part* | wc -l); n4=$(ls $P-4K.mp4.part* | wc -l)
H1=$(sha256sum "$F1"|cut -c1-64); H4=$(sha256sum "$F4"|cut -c1-64)
S1=$(( $(stat -c%s "$F1")/1000000 )); S4=$(( $(stat -c%s "$F4")/1000000 ))
B=https://github.com/nullemon/do-my-task/raw/$BR
l1=$(seq -f "%02g" 0 $((n1-1)) | tr '\n' ' '); l4=$(seq -f "%02g" 0 $((n4-1)) | tr '\n' ' ')
j1=$(seq -f "$P-1080p.mp4.part%02g" 0 $((n1-1)) | paste -sd+); j4=$(seq -f "$P-4K.mp4.part%02g" 0 $((n4-1)) | paste -sd+)
cat > Get-$P.bat <<EOF
@echo off
title $TITLE - download
cd /d "%~dp0"
echo Downloading $TITLE full quality (1080p $S1 MB + 4K $S4 MB)...
for %%i in ($l1) do (
  echo   1080p piece %%i
  curl -L --fail --retry 3 -o $P-1080p.mp4.part%%i "$B/$P-1080p.mp4.part%%i" || goto :fail
)
for %%i in ($l4) do (
  echo   4K piece %%i
  curl -L --fail --retry 3 -o $P-4K.mp4.part%%i "$B/$P-4K.mp4.part%%i" || goto :fail
)
echo Joining...
copy /b $j1 $P-1080p.mp4 >nul || goto :fail
copy /b $j4 $P-4K.mp4 >nul || goto :fail
echo Checking files...
certutil -hashfile $P-1080p.mp4 SHA256 | find /i "$H1" >nul || goto :bad
certutil -hashfile $P-4K.mp4 SHA256 | find /i "$H4" >nul || goto :bad
del $P-1080p.mp4.part* $P-4K.mp4.part*
echo.
echo DONE. $P-1080p.mp4 and $P-4K.mp4 are ready (verified).
pause
exit /b 0
:bad
echo CHECK FAILED - a file does not match. Run this script again.
pause
exit /b 1
:fail
echo Download failed. Check your internet connection and run this script again.
pause
exit /b 1
EOF
sed -i 's/$/\r/' Get-$P.bat
git init -q -b $BR && git add . && git -c user.email=noreply@anthropic.com -c user.name=Claude commit -qm "Delivery: $TITLE (temporary)" && git remote add origin $(git -C /home/user/do-my-task remote get-url origin)
git push -q -f origin $BR 2>&1 | grep -vE "warning|^remote|expected 'acknowledgments'" || true
for f in Get-$P.bat $P-1080p.mp4.part00 $P-4K.mp4.part$(printf %02d $((n4-1))); do echo "$f $(curl -sL -o /dev/null -w '%{http_code} %{size_download}' --max-time 300 $B/$f) local $(stat -c%s $f)"; done
echo "LINK $B/Get-$P.bat"
