#!/usr/bin/env bash
set -euo pipefail

# Aggressively keep the download engines fresh: yt-dlp/spotdl break whenever
# YouTube/SoundCloud change their sites. Controlled by YTDLP_AUTO_UPDATE.
if [ "${YTDLP_AUTO_UPDATE:-true}" = "true" ]; then
  echo "[entrypoint] Updating yt-dlp + spotdl…"
  pip install --no-cache-dir --upgrade --user yt-dlp spotdl || \
    echo "[entrypoint] update failed (continuing with bundled versions)"
fi

echo "[entrypoint] Starting: $*"
exec "$@"
