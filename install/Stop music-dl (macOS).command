#!/bin/bash
# Double-click to STOP music-dl. Your downloads and login are kept.

NAME="music-dl"

if ! command -v docker >/dev/null 2>&1 || ! docker info >/dev/null 2>&1; then
  echo "Docker isn't running — music-dl is already stopped."
  exit 0
fi

if docker ps --format '{{.Names}}' | grep -qx "$NAME"; then
  docker stop "$NAME" >/dev/null
  echo "⏹  music-dl stopped. It won't run in the background."
  echo "    Double-click 'Start music-dl' whenever you want to use it again."
else
  echo "music-dl is not running."
fi
