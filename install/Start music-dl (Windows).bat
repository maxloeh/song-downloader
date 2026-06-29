@echo off
REM Double-click this file to start music-dl. No coding needed.
REM It installs nothing except (once) Docker Desktop, which it will prompt for.

setlocal
set IMAGE=ghcr.io/maxloeh/song-downloader:latest
set NAME=music-dl
set PORT=8080
set DOWNLOADS=%USERPROFILE%\Music\music-dl

echo ----------------------------------------------
echo    music-dl launcher
echo ----------------------------------------------

REM 1. Docker installed?
where docker >nul 2>nul
if errorlevel 1 (
  echo Docker Desktop is required ^(a free app^). Opening the download page...
  echo Install it, start it, then double-click this launcher again.
  start "" "https://www.docker.com/products/docker-desktop/"
  pause
  exit /b 1
)

REM 2. Docker running?
docker info >nul 2>nul
if errorlevel 1 (
  echo Please start Docker Desktop, wait for it to finish loading, then run this again.
  pause
  exit /b 1
)

REM 3. Get the latest version and (re)start the app.
if not exist "%DOWNLOADS%" mkdir "%DOWNLOADS%"
echo Downloading the latest music-dl... ^(first time can take a few minutes^)
docker pull %IMAGE%
docker rm -f %NAME% >nul 2>nul
docker run -d --name %NAME% --restart unless-stopped -p %PORT%:8080 -v "%DOWNLOADS%:/downloads" %IMAGE%

REM 4. Open it.
timeout /t 2 >nul
start "" "http://localhost:%PORT%"
echo.
echo music-dl is running:  http://localhost:%PORT%
echo Songs are saved to:   %DOWNLOADS%
echo First time? The app will ask you to create a username ^& password.
echo.
echo You can close this window. To stop the app, quit Docker Desktop.
pause
