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

> #### 🍎 Mac: "Apple could not verify…" / *"Apple konnte nicht überprüfen…"*
> This is normal for free apps not from the App Store — you allow it **once**:
>
> 1. Double-click the file. You'll get the warning — click **Done** (*Fertig*).
>    **Do NOT click "Move to Trash" / *In den Papierkorb legen*.**
> 2. Open **System Settings** (*Systemeinstellungen*) → **Privacy & Security**
>    (*Datenschutz & Sicherheit*).
> 3. Scroll down — you'll see *"Start music-dl … was blocked"*. Click
>    **Open Anyway** (*Trotzdem öffnen*) and confirm with Touch ID / your password.
> 4. Double-click the launcher again → click **Open** (*Öffnen*). Done forever.
>
> *(Older macOS: right-click the file → **Open** → **Open** works directly.)*

> #### 🪟 Windows: "Windows protected your PC"
> Click **More info** → **Run anyway**. Once only.

### 3. Create your account
Your browser opens to **http://localhost:8080**. The first time, it asks you to
choose a **username and password** — these are just for you. Done!

## Using it
- Paste a SoundCloud or Spotify link, pick a format/quality, hit **Download**.
- Finished songs are saved to **`Music/music-dl`** in your home folder.
- **Spotify already works** — no setup needed (it's preconfigured).
- Optional: connect your **SoundCloud** account in the app (only needed for
  private tracks or original-quality downloads) — there's a "Connect" panel with
  step-by-step instructions.

## Start & stop (it only runs when you want it to)

Three double-click files do everything — no background hogging:

| Double-click… | What it does |
|---|---|
| **Start music-dl** | Starts/opens the app. First time downloads it; after that it **resumes instantly** and opens your browser. |
| **Stop music-dl** | Stops it so it's not using your computer. Your downloads & login are kept. |
| **Update music-dl** | Gets the newest version, then opens it. (Only when you want updates.) |

It does **not** auto-start on its own — it runs only after you hit **Start**, and
stays off after **Stop** (even if you restart your computer).

> To go fully idle you can also quit Docker Desktop; next time just hit **Start**
> (it'll relaunch Docker for you).

> Mac: each of these files needs the one-time "Open Anyway" step the first time —
> see the macOS box above.

## Heads-up
- Spotify links are matched to audio on YouTube (Spotify itself is download-locked),
  so quality is capped at ~128–256 kbps.
- Some SoundCloud tracks are protected by SoundCloud and can't be downloaded
  directly — the app will automatically try to find them on YouTube instead.
- This is for private use, for music you're entitled to download.
