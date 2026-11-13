@echo off
REM Makes Whisper transcripts for clips you ALREADY downloaded (stories 1-6), then a tiny zip to upload.
call "%~dp0FETCH_DOG_FOOTAGE.bat" transcripts 1-6
