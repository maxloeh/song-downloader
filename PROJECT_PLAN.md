# Project Plan: Self-Hosted Music Downloader (SoundCloud + Spotify)

> **Hand this file to Claude Code.** It is a complete build specification. Read it
> fully, then propose a phased implementation plan and execute it phase by phase,
> confirming with me at the end of each phase.

---

## 1. Goal

A self-hosted web app that lets me and a few friends download individual songs or
whole playlists from **SoundCloud** and **Spotify**, with selectable format and
quality, and **fully populated metadata including embedded cover art**. It must live
in a private GitHub repo and be as easy as possible to self-host (single
`docker compose up`). It is **not** publicly accessible — access is gated by auth and
intended to run behind Tailscale or a reverse proxy.

---

## 2. Critical technical reality (read before designing)

This shapes the whole architecture — do not skip it.

- **SoundCloud** audio is downloaded **directly** via `yt-dlp` (native extractor).
  Original/high quality is possible only when the uploader enabled downloads;
  otherwise it's the standard stream.
- **Spotify** audio **cannot** be downloaded directly — streams are DRM-protected.
  `spotDL` is a **metadata-matching engine**: it pulls track metadata (title, artist,
  album, year, track number, ISRC, cover art, lyrics) from the **Spotify API**, then
  finds the closest match on **YouTube Music** and downloads *that* via `yt-dlp`,
  finally embedding the Spotify metadata into the file. So:
  - The audio source for "Spotify" downloads is effectively YouTube.
  - Bitrate is capped by the YouTube source (~128 kbps standard, up to ~256 kbps).
    Exporting FLAC from a Spotify link does **not** create true lossless audio.
  - This path produces the **best metadata/cover** of the two sources.
- `spotDL` itself depends on `yt-dlp` + `ffmpeg`. Keep `yt-dlp` updated aggressively —
  it breaks whenever YouTube/SoundCloud change their sites. Build an auto-update path.
- `ffmpeg` is a hard runtime dependency for format conversion and tag/cover embedding.
- Spotify tightened API access. `spotDL` now defaults to a lighter no-API client, but
  for reliability the user **must** supply their own Spotify Developer
  `client_id`/`client_secret` (free to create). The app should pass these to spotDL.
- Some YouTube downloads require a JS runtime (**Deno**) to succeed; install it in the
  container so playlist downloads don't silently drop tracks.

---

## 3. Tech stack

| Layer            | Choice                                                                 |
|------------------|------------------------------------------------------------------------|
| Backend          | Python 3.12, **FastAPI** + Uvicorn                                      |
| Download engines | **yt-dlp** (SoundCloud + actual audio fetch), **spotdl** (Spotify path)|
| Audio processing | **ffmpeg** (system), **mutagen** (tag fixups if needed)                |
| Job/queue        | In-process `asyncio` task queue + job registry; **SQLite** for history |
| Live progress    | **WebSocket** (FastAPI native), polling fallback                       |
| Frontend         | **React + Vite + Tailwind**, built in a multi-stage Docker step and    |
|                  | served as static files by FastAPI (single container, user never touches node) |
| Auth             | HTTP Basic Auth via FastAPI dependency, credentials from env vars      |
| Packaging        | **Docker** + **docker compose**, one service, one downloads volume     |
| JS runtime       | **Deno** (for yt-dlp YouTube edge cases)                                |

If the React build step proves heavy, a vanilla-JS/Alpine.js frontend served
statically is an acceptable fallback — but default to React for a clean GUI.

---

## 4. Functional requirements

1. **Input**: paste one URL (or several, newline-separated). The app auto-detects the
   source (SoundCloud vs Spotify) and whether it's a single track, playlist, or album.
2. **Format selection** (per download): `mp3`, `m4a`, `opus`, `flac`, `ogg`, `wav`.
3. **Quality selection**: bitrate options (e.g. `128k`, `192k`, `256k`, `320k`, plus
   `best`/`auto`). For SoundCloud, also expose an "original file if available" toggle.
4. **Metadata + cover (must-have)**: every downloaded file must have title, artist,
   album, track number, year, and **embedded cover art** wherever the source provides
   it. Spotify path uses spotDL's metadata; SoundCloud path uses yt-dlp postprocessors
   (`FFmpegMetadata` + `EmbedThumbnail`) and parses `Artist - Title` from the track
   title when structured fields are missing.
5. **Playlists**: download whole SoundCloud sets and Spotify playlists/albums; each
   track is a separate job in the queue; playlist files land in a per-playlist folder.
6. **Queue + live progress**: show queued / downloading / converting / done / failed
   per track, with a progress percentage and a clear error message on failure.
7. **Results**: list completed files with per-file download links and a "download all
   as zip" option. Optionally browse the output directory.
8. **History**: persist past jobs (SQLite) so the list survives restarts.
9. **Auth**: the whole UI and API require login (Basic Auth, shared or per-user creds).

---

## 5. Repository structure

```
music-dl/
├── README.md                  # setup, self-hosting, Spotify creds, usage
├── docker-compose.yml
├── Dockerfile                 # multi-stage: node build → python runtime
├── .env.example               # all config, documented
├── .gitignore
├── LICENSE                    # note: private repo; choose a license or "all rights reserved"
├── backend/
│   ├── pyproject.toml         # use uv or pip
│   ├── app/
│   │   ├── main.py            # FastAPI app, static serving, WebSocket
│   │   ├── auth.py            # Basic Auth dependency
│   │   ├── config.py          # env-var settings (pydantic-settings)
│   │   ├── models.py          # Job, JobStatus, enums, SQLite models
│   │   ├── queue.py           # asyncio job queue + worker pool + progress events
│   │   ├── sources/
│   │   │   ├── base.py        # Source interface: detect(), enumerate(), download()
│   │   │   ├── soundcloud.py  # yt-dlp wrapper
│   │   │   └── spotify.py     # spotdl wrapper
│   │   ├── metadata.py        # post-download tag/cover verification + fixups
│   │   ├── routes/
│   │   │   ├── downloads.py   # POST /api/download, GET /api/jobs, WS /ws
│   │   │   └── files.py       # GET /api/files, file + zip serving
│   │   └── db.py
│   └── tests/
└── frontend/
    ├── package.json
    ├── vite.config.ts
    └── src/                   # React UI (paste box, options, queue, results)
```

---

## 6. Backend design notes

### Source abstraction
Define a `Source` interface so SoundCloud and Spotify are interchangeable:
```python
class Source(Protocol):
    def matches(self, url: str) -> bool: ...
    def enumerate(self, url: str) -> list[TrackRef]: ...   # 1 for a track, N for a playlist
    async def download(self, track: TrackRef, opts: DownloadOptions,
                       on_progress: Callable) -> Path: ...
```
A `resolve_source(url)` factory picks the right implementation from the URL host.

### SoundCloud (`yt-dlp` via its Python API, not the CLI)
- Use `yt_dlp.YoutubeDL` with options built from the user's format/quality.
- Postprocessors for the must-have metadata/cover:
  - `FFmpegExtractAudio` (target codec from selected format)
  - `FFmpegMetadata` (write tags)
  - `EmbedThumbnail` (embed cover; set `writethumbnail=True`)
- SoundCloud tags are often sparse (frequently only title + uploader). Parse
  `"Artist - Title"` patterns to fill artist/title when structured fields are absent.
- For original quality, pass an auth token if the user configured one and request the
  original download format; otherwise fall back to the best stream.
- Hook `progress_hooks` to emit progress events to the queue.

### Spotify (`spotdl` via its Python API)
- Initialize spotDL with the user's Spotify `client_id`/`client_secret` from env.
- Use spotDL to enumerate a track/album/playlist into songs, then download with the
  selected `format` and `bitrate`; spotDL handles YouTube matching + metadata + cover
  embedding. Expose spotDL's audio-provider fallback list (`youtube-music`, `youtube`,
  `soundcloud`) in config.
- Surface spotDL progress into the same job/progress model used by SoundCloud.
- Be explicit in the UI/result that the audio came from a YouTube match.

### Queue & progress
- An `asyncio.Queue` of jobs consumed by a small worker pool
  (`MAX_CONCURRENT_DOWNLOADS`, default 3).
- Each job has: id, source, url, options, status, progress %, output path(s), error.
- Push status changes over a WebSocket channel keyed by job id; the frontend
  subscribes. Provide `GET /api/jobs` polling as a fallback.
- Persist jobs to SQLite so history survives restarts; in-memory registry mirrors it.

### Metadata verification
After every download, verify with `mutagen` that title/artist/album/cover are present;
if the cover is missing but a thumbnail was fetched, embed it as a fixup. Log a warning
on any track that ends up without a cover.

---

## 7. Frontend design notes

Single page, clean and minimal:
- A textarea for one or more URLs.
- A format dropdown + quality dropdown + "original (SoundCloud)" toggle.
- A "Download" button that creates jobs.
- A live **queue list**: each row shows source icon, track name, status badge, progress
  bar, and (on done) a download link; (on fail) the error.
- A **completed** section with per-file links and a "Download all (zip)" button.
- Auth handled by the browser's Basic Auth prompt (or a simple login screen that stores
  credentials for the session).
- Keep it responsive so it works from a phone on the same Tailscale network.

Use the project's frontend-design conventions for a non-generic look; avoid default
template styling.

---

## 8. Configuration (`.env`)

Document every variable in `.env.example`:

```
# Auth (required) — shared or per-user
APP_USERNAME=changeme
APP_PASSWORD=changeme

# Spotify Developer credentials (required for reliable Spotify metadata)
# Create at https://developer.spotify.com/dashboard
SPOTIFY_CLIENT_ID=
SPOTIFY_CLIENT_SECRET=

# SoundCloud (optional) — only needed for original-quality / private downloads
SOUNDCLOUD_AUTH_TOKEN=

# Behavior
MAX_CONCURRENT_DOWNLOADS=3
DEFAULT_FORMAT=mp3
DEFAULT_BITRATE=320k
DOWNLOAD_DIR=/downloads
OUTPUT_TEMPLATE=%(playlist_title)s/%(title)s.%(ext)s

# Maintenance
YTDLP_AUTO_UPDATE=true        # pip install -U yt-dlp on container start
```

---

## 9. Self-hosting

### Dockerfile (multi-stage)
1. **Stage 1 (node)**: build the React frontend (`npm ci && npm run build`).
2. **Stage 2 (python:3.12-slim)**: install `ffmpeg` and `deno`, `pip install` backend
   deps + `yt-dlp` + `spotdl`, copy backend code and the built frontend `dist/`.
   Run as a non-root user. Entrypoint optionally runs `pip install -U yt-dlp` when
   `YTDLP_AUTO_UPDATE=true`, then starts Uvicorn.

### docker-compose.yml
- One service, restart `unless-stopped`, port mapped (e.g. `8080:8080`).
- Bind-mount/volume for `/downloads` (ensure writable by the container UID/GID).
- Env from `.env`.
- Optional: a companion **watchtower** service to auto-pull image updates, since
  `yt-dlp` needs frequent updates.

### Keeping yt-dlp working
yt-dlp breaks when sites change. Combine the `YTDLP_AUTO_UPDATE` entrypoint step with
periodic image rebuilds (GitHub Actions on a schedule, or watchtower). Document this in
the README — it's the #1 cause of "it suddenly stopped downloading".

### Recommended exposure (private, not public)
Strongly recommend **Tailscale**: install it on the host, access the app via its
Tailscale IP/MagicDNS, and only people I add to my tailnet can reach it. This satisfies
"not publicly accessible" far better than port-forwarding. Document a Tailscale path as
primary, and a Caddy/Traefik reverse-proxy-with-HTTPS path as the alternative. Even on
Tailscale, keep Basic Auth on as defense in depth.

---

## 10. Build phases (execute in order, confirm after each)

1. **Scaffold**: repo structure, FastAPI hello-world, Dockerfile + compose, `.env`
   handling, Basic Auth, README skeleton. Acceptance: `docker compose up` serves an
   authenticated empty page.
2. **SoundCloud single track**: yt-dlp wrapper with format/quality selection.
   Acceptance: paste a SoundCloud track URL → get a correctly-formatted audio file.
3. **Metadata + cover**: postprocessors + mutagen verification/fixups. Acceptance:
   downloaded SoundCloud file has title/artist/album and an embedded cover.
4. **Playlists (SoundCloud)**: enumerate a set into N jobs into per-playlist folders.
5. **Spotify path**: spotdl integration with user-supplied API creds, format/bitrate,
   metadata + cover. Acceptance: paste a Spotify track and playlist → tagged files with
   covers; UI notes the YouTube audio source.
6. **Queue + live progress**: async worker pool, WebSocket progress, status badges,
   concurrency limit, error surfacing.
7. **Frontend**: full React UI (paste box, options, queue, results, zip download).
8. **History + files**: SQLite persistence, file listing, per-file + zip serving.
9. **Hardening & docs**: auto-update yt-dlp, watchtower note, Tailscale guide,
   complete README, `.env.example`, basic tests for source detection and tagging.

Acceptance criteria for the whole project: from a phone on my Tailscale network, I log
in, paste a SoundCloud playlist URL and a Spotify track URL, pick `flac`/`320k`, and get
queued downloads with live progress and fully tagged, cover-art-embedded files I can pull
down individually or as a zip.

---

## 11. Legal / usage note (put a short version in the README)

This tool is for **private use** among a closed group, intended for content the users
are entitled to download: their own uploads, tracks creators made freely downloadable,
and Creative Commons material. Downloading copyrighted tracks without permission can
violate SoundCloud's/Spotify's terms and copyright law. Keep the repo private and the
instance non-public. Users are responsible for their own use.

---

## 12. Key gotchas checklist (for Claude Code)

- [ ] `ffmpeg` present in the image — without it, conversion and cover embedding fail.
- [ ] `deno` present — some YouTube downloads (and thus Spotify-path tracks) need it.
- [ ] Spotify creds wired into spotdl; degrade gracefully with a clear message if absent.
- [ ] yt-dlp auto-update on start + documented rebuild cadence.
- [ ] Container runs as non-root; `/downloads` writable by that UID/GID.
- [ ] Be honest in the UI about the Spotify→YouTube audio source and its bitrate ceiling.
- [ ] Sanitize filenames; handle very long playlist names; avoid path traversal in file serving.
- [ ] Don't leak Spotify/SoundCloud credentials into logs or the API responses.
