@echo off
REM Double-click to START / open music-dl. Resumes instantly after the first time.
setlocal
set IMAGE=ghcr.io/maxloeh/song-downloader:latest
set NAME=music-dl
set PORT=8080
set DOWNLOADS=%USERPROFILE%\Music\music-dl

echo Starting music-dl...

where docker >nul 2>nul
if errorlevel 1 (
  echo Docker Desktop is required ^(free^). Opening the download page...
  echo Install it, start it, then double-click this again.
  start "" "https://www.docker.com/products/docker-desktop/"
  pause & exit /b 1
)
docker info >nul 2>nul
if errorlevel 1 (
  echo Please start Docker Desktop, wait for it to load, then run this again.
  pause & exit /b 1
)
if not exist "%DOWNLOADS%" mkdir "%DOWNLOADS%"

docker ps --format "{{.Names}}" | findstr /x "%NAME%" >nul && goto running
docker ps -a --format "{{.Names}}" | findstr /x "%NAME%" >nul && goto resume

echo First time - downloading music-dl ^(a few minutes^)...
docker pull %IMAGE%
docker run -d --name %NAME% --restart no -p %PORT%:8080 -v "%DOWNLOADS%:/downloads" %IMAGE%
goto open

:resume
echo Resuming...
docker start %NAME% >nul
goto open

:running
echo Already running.

:open
timeout /t 1 >nul
start "" "http://localhost:%PORT%"
echo.
echo music-dl is open: http://localhost:%PORT%
echo Songs are saved to %DOWNLOADS%
echo Done for now? Double-click "Stop music-dl" to free up your computer.
pause
