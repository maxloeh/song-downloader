@echo off
REM Double-click to UPDATE music-dl to the newest version, then open it.
setlocal
set IMAGE=ghcr.io/maxloeh/song-downloader:latest
set NAME=music-dl
set PORT=8080
set DOWNLOADS=%USERPROFILE%\Music\music-dl

docker info >nul 2>nul
if errorlevel 1 (
  echo Please start Docker Desktop, then run this again.
  pause & exit /b 1
)
if not exist "%DOWNLOADS%" mkdir "%DOWNLOADS%"

echo Updating music-dl to the latest version...
docker pull %IMAGE%
docker rm -f %NAME% >nul 2>nul
docker run -d --name %NAME% --restart no -p %PORT%:8080 -v "%DOWNLOADS%:/downloads" %IMAGE%
timeout /t 1 >nul
start "" "http://localhost:%PORT%"
echo Updated and running at http://localhost:%PORT%
pause
