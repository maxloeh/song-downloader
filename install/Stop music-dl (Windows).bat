@echo off
REM Double-click to STOP music-dl. Your downloads and login are kept.
setlocal
set NAME=music-dl

docker info >nul 2>nul
if errorlevel 1 (
  echo Docker isn't running - music-dl is already stopped.
  pause & exit /b 0
)

docker ps --format "{{.Names}}" | findstr /x "%NAME%" >nul && goto stopit
echo music-dl is not running.
pause & exit /b 0

:stopit
docker stop %NAME% >nul
echo music-dl stopped. It won't run in the background.
echo Double-click "Start music-dl" whenever you want to use it again.
pause
