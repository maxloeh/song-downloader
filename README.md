# 🎵 Self-Hosted Music Downloader

A private, self-hosted web app to download individual songs or whole playlists
from **SoundCloud** and **Spotify**, with selectable format/quality and fully
populated metadata **including embedded cover art**.

One `docker compose up`. Gated by auth. Built to run behind **Tailscale** or a
reverse proxy — **not** meant to be public.

> ⚖️ **Usage:** For private use among a closed group, for content you are
> entitled to download (your own uploads, tracks creators made freely
> downloadable, Creative Commons). Downloading copyrighted tracks without
> permission can violate SoundCloud's/Spotify's terms and copyright law. Keep
> this repo private and the instance non-public. You are responsible for your use.

---

## How it works (read this)

| Source | Audio comes from | Notes |
|--------|------------------|-------|
| **SoundCloud** | SoundCloud directly (`yt-dlp`) | Original/high quality only when the uploader enabled downloads; otherwise the standard stream. |
| **Spotify** | **YouTube** (`spotDL` → `yt-dlp`) | Spotify streams are DRM-protected and **cannot** be downloaded directly. spotDL pulls *metadata + cover* from Spotify and downloads the closest **YouTube** match. **Bitrate is capped by YouTube (~128–256 kbps).** Exporting FLAC from a Spotify link does **not** create true lossless audio. |

The UI is explicit about the Spotify→YouTube audio source.

---

## Quick start

```bash
git clone <your-private-repo> music-dl && cd music-dl
cp .env.example .env
# edit .env: set APP_USERNAME/APP_PASSWORD, and ideally Spotify creds
docker compose up -d --build
```

Open `http://<host>:8080`, log in with your Basic Auth credentials, paste links.

Downloads land in `./downloads` on the host.

---

## Configuration (`.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `APP_USERNAME` / `APP_PASSWORD` | ✅ | Basic Auth credentials gating the whole app. |
| `SPOTIFY_CLIENT_ID` / `SPOTIFY_CLIENT_SECRET` | recommended | Free Spotify Developer app for reliable Spotify metadata. Create at <https://developer.spotify.com/dashboard>. Without them, spotDL uses a limited no-API mode. |
| `SOUNDCLOUD_AUTH_TOKEN` | optional | `oauth_token` from a logged-in SoundCloud session, for original-quality/private downloads. |
| `MAX_CONCURRENT_DOWNLOADS` | | Worker pool size (default `3`). |
| `DEFAULT_FORMAT` / `DEFAULT_BITRATE` | | UI defaults (`mp3` / `320k`). |
| `DOWNLOAD_DIR` | | In-container download path (default `/downloads`). |
| `SPOTDL_AUDIO_PROVIDERS` | | Fallback order, e.g. `youtube-music,youtube`. |
| `YTDLP_AUTO_UPDATE` | | `pip install -U yt-dlp spotdl` on container start (default `true`). |

### Getting Spotify credentials
1. Go to <https://developer.spotify.com/dashboard> → **Create app**.
2. Any name/description; redirect URI can be `http://localhost`.
3. Copy the **Client ID** and **Client Secret** into `.env`.

---

## Keeping it working (important)

`yt-dlp` breaks whenever YouTube/SoundCloud change their sites — this is the #1
cause of "it suddenly stopped downloading." Mitigations, all built in:

1. **`YTDLP_AUTO_UPDATE=true`** updates `yt-dlp`/`spotdl` on every container start.
2. **Periodic rebuilds** — rebuild the image regularly (`docker compose build --pull`).
3. **Watchtower** (optional) auto-pulls rebuilt images:
   ```bash
   docker compose --profile watchtower up -d
   ```

`ffmpeg` and `deno` are baked into the image (conversion/cover embedding, and
some YouTube extractions respectively).

---

## Recommended exposure: Tailscale (private)

Strongly recommended over port-forwarding:

1. Install Tailscale on the host and `tailscale up`.
2. Reach the app at `http://<host-tailscale-ip>:8080` (or MagicDNS name).
3. Only devices on your tailnet can connect.

Keep Basic Auth on even on Tailscale — defense in depth.

### Alternative: reverse proxy with HTTPS (Caddy)
```caddy
music.example.com {
    reverse_proxy localhost:8080
}
```
Bind the app to `127.0.0.1:8080` in `docker-compose.yml` when proxying.

---

## Local development

**Backend:**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
# requires ffmpeg installed locally
DOWNLOAD_DIR=./downloads APP_USERNAME=dev APP_PASSWORD=dev \
  uvicorn app.main:app --reload --port 8080
```

**Frontend (with hot reload, proxying to the backend above):**
```bash
cd frontend
npm install
npm run dev   # http://localhost:5173
```

**Tests:**
```bash
cd backend && pytest
```

---

## Architecture

```
Browser (React SPA, Basic Auth)
      │  POST /api/download · GET /api/jobs · WS /api/ws · GET /api/files
      ▼
FastAPI ── JobQueue (asyncio worker pool) ── SQLite history
      │            │
      │            ├── SoundCloudSource  → yt-dlp (+ffmpeg postprocessors)
      │            └── SpotifySource     → spotDL → yt-dlp (YouTube match)
      │                                     → mutagen verify/fixup cover
      └── serves built frontend (backend/static)
```

- **Source abstraction** (`app/sources/base.py`): `matches()` / `enumerate()` /
  `download()`; `resolve_source(url)` picks SoundCloud vs Spotify by host.
- **Queue** (`app/queue.py`): `MAX_CONCURRENT_DOWNLOADS` workers, progress pushed
  over a WebSocket broadcaster; `GET /api/jobs` is the polling fallback.
- **Metadata** (`app/metadata.py`): after each download, verifies
  title/artist/album/cover with `mutagen`; embeds a sidecar thumbnail if the
  cover is missing; parses `Artist - Title` to fill sparse SoundCloud tags.
- **Files** (`app/routes/files.py`): listing, per-file serving, and zip-all,
  with path-traversal protection.

---

## Project layout

```
.
├── docker-compose.yml      # one service + optional watchtower
├── Dockerfile              # multi-stage: node build → python runtime
├── docker/entrypoint.sh    # yt-dlp/spotdl auto-update, then uvicorn
├── .env.example
├── backend/
│   ├── pyproject.toml
│   ├── app/                # FastAPI app (see Architecture)
│   └── tests/
└── frontend/               # React + Vite + Tailwind (built to backend/static)
```
