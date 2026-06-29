# 🎵 music-dl — Setup (no coding needed)

Run your own private music downloader in a few clicks.

## What you need
- A Mac or Windows PC.
- **Docker Desktop** (free) — the launcher will send you to the download page if you don't have it.

## Steps

### 1. Install Docker Desktop (one time)
Download it here → https://www.docker.com/products/docker-desktop/
Install it like any normal app, then **open it** (wait until the whale icon says it's running).

### 2. Start music-dl
- **Mac:** double-click **`Start music-dl (macOS).command`**
- **Windows:** double-click **`Start music-dl (Windows).bat`**

The first time, it downloads the app (a few minutes). After that it's quick.

> Mac note: if you see *"cannot be opened because it is from an unidentified developer"*,
> right-click the file → **Open** → **Open**. You only need to do this once.

### 3. Create your account
Your browser opens to **http://localhost:8080**. The first time, it asks you to
choose a **username and password** — these are just for you. Done!

## Using it
- Paste a SoundCloud or Spotify link, pick a format/quality, hit **Download**.
- Finished songs are saved to **`Music/music-dl`** in your home folder.
- Optional, in the app: connect **Spotify** (for better metadata) and your
  **SoundCloud** account (for tracks that need a login). Each has a "Connect"
  panel with step-by-step instructions.

## Everyday use
- **Open it again:** just go to http://localhost:8080 (it keeps running in the
  background as long as Docker Desktop is open).
- **Update to the latest version:** double-click the launcher again.
- **Stop it:** quit Docker Desktop.

## Heads-up
- Spotify links are matched to audio on YouTube (Spotify itself is download-locked),
  so quality is capped at ~128–256 kbps.
- Some SoundCloud tracks are protected by SoundCloud and can't be downloaded
  directly — the app will automatically try to find them on YouTube instead.
- This is for private use, for music you're entitled to download.
