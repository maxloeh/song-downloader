#!/bin/bash
# Double-click this file to start music-dl. No coding needed.
# It installs nothing except (once) Docker Desktop, which it will prompt for.

set -e
IMAGE="ghcr.io/maxloeh/song-downloader:latest"
NAME="music-dl"
PORT="8080"
DOWNLOADS="$HOME/Music/music-dl"

echo "──────────────────────────────────────────────"
echo "  🎵  music-dl launcher"
echo "──────────────────────────────────────────────"

# 1. Docker installed?
if ! command -v docker >/dev/null 2>&1; then
  osascript -e 'display dialog "music-dl needs Docker Desktop (a free app). I will open the download page. Install it, start it, then double-click this launcher again." buttons {"Open download page"} default button 1' >/dev/null 2>&1 || true
  open "https://www.docker.com/products/docker-desktop/"
  exit 1
fi

# 2. Docker running?
if ! docker info >/dev/null 2>&1; then
  echo "Starting Docker Desktop… (this can take a minute)"
  open -a Docker || true
  for _ in $(seq 1 60); do docker info >/dev/null 2>&1 && break; sleep 2; done
fi
if ! docker info >/dev/null 2>&1; then
  echo "Docker didn't start. Please open Docker Desktop manually, then try again."
  exit 1
fi

# 3. Get the latest version and (re)start the app.
mkdir -p "$DOWNLOADS"
echo "Downloading the latest music-dl… (first time can take a few minutes)"
docker pull "$IMAGE"
docker rm -f "$NAME" >/dev/null 2>&1 || true
docker run -d --name "$NAME" --restart unless-stopped \
  -p "${PORT}:8080" -v "$DOWNLOADS:/downloads" "$IMAGE" >/dev/null

# 4. Open it.
sleep 2
open "http://localhost:${PORT}"
echo ""
echo "✅  music-dl is running:  http://localhost:${PORT}"
echo "    Songs are saved to:   $DOWNLOADS"
echo "    First time? The app will ask you to create a username & password."
echo ""
echo "You can close this window. To stop the app, quit Docker Desktop."
