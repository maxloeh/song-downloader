#!/bin/bash
# Double-click to START / open music-dl. Resumes instantly after the first time.

IMAGE="ghcr.io/maxloeh/song-downloader:latest"
NAME="music-dl"
PORT="8080"
DOWNLOADS="$HOME/Music/music-dl"

echo "🎵 Starting music-dl…"

# Docker installed?
if ! command -v docker >/dev/null 2>&1; then
  osascript -e 'display dialog "music-dl needs Docker Desktop (a free app). I will open the download page. Install it, start it, then double-click this again." buttons {"Open download page"} default button 1' >/dev/null 2>&1 || true
  open "https://www.docker.com/products/docker-desktop/"
  exit 1
fi

# Docker running?
if ! docker info >/dev/null 2>&1; then
  echo "Starting Docker Desktop… (can take a minute)"
  open -a Docker || true
  for _ in $(seq 1 60); do docker info >/dev/null 2>&1 && break; sleep 2; done
fi
if ! docker info >/dev/null 2>&1; then
  echo "Docker didn't start. Open Docker Desktop manually, then try again."
  exit 1
fi

mkdir -p "$DOWNLOADS"

if docker ps --format '{{.Names}}' | grep -qx "$NAME"; then
  echo "Already running."
elif docker ps -a --format '{{.Names}}' | grep -qx "$NAME"; then
  echo "Resuming…"
  docker start "$NAME" >/dev/null
else
  echo "First time — downloading music-dl (a few minutes)…"
  docker pull "$IMAGE"
  docker run -d --name "$NAME" --restart no \
    -p "${PORT}:8080" -v "$DOWNLOADS:/downloads" "$IMAGE" >/dev/null
fi

sleep 1
open "http://localhost:${PORT}"
echo ""
echo "✅  music-dl is open:  http://localhost:${PORT}"
echo "    Songs are saved to: $DOWNLOADS"
echo "    Done for now? Double-click 'Stop music-dl' to free up your computer."
