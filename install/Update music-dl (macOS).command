#!/bin/bash
# Double-click to UPDATE music-dl to the newest version, then open it.

IMAGE="ghcr.io/maxloeh/song-downloader:latest"
NAME="music-dl"
PORT="8080"
DOWNLOADS="$HOME/Music/music-dl"

command -v docker >/dev/null 2>&1 || { echo "Install Docker Desktop first."; exit 1; }
if ! docker info >/dev/null 2>&1; then
  open -a Docker || true
  for _ in $(seq 1 60); do docker info >/dev/null 2>&1 && break; sleep 2; done
fi
docker info >/dev/null 2>&1 || { echo "Docker didn't start."; exit 1; }

mkdir -p "$DOWNLOADS"
echo "Updating music-dl to the latest version…"
docker pull "$IMAGE"
docker rm -f "$NAME" >/dev/null 2>&1 || true
docker run -d --name "$NAME" --restart no \
  -p "${PORT}:8080" -v "$DOWNLOADS:/downloads" "$IMAGE" >/dev/null
sleep 1
open "http://localhost:${PORT}"
echo "✅  Updated and running:  http://localhost:${PORT}"
