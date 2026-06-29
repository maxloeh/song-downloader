# Handoff: music-dl UI

## Overview
High-fidelity UI design for **music-dl** — a private, self-hosted web app to download
songs and playlists from SoundCloud and Spotify, with format/quality selection, live
download progress, and grouped completed results. The design covers: a login gate, the
main paste/options screen (with empty + populated states), the download queue with every
status state, the completed section grouped by playlist, and a component sheet.

The target codebase already exists: **`maxloeh/song-downloader`** — a React + Vite +
Tailwind frontend (`frontend/`) served by a FastAPI backend. This design is a visual
redesign of that existing frontend. It reuses the repo's data model verbatim
(`Job`, `JobStatus`, `Source`, `DownloadOptions`, `AppConfig`, `FileItem` in
`frontend/src/types.ts`) and the existing API/WebSocket layer (`frontend/src/api.ts`).
The work is to restyle and extend the existing components — not to change the backend.

## About the Design Files
The file in this bundle (`Music-dl.dc.html`) is a **design reference created in HTML** —
a single self-contained prototype showing the intended look and behavior. It is **not**
production code to copy directly. Recreate it in the existing React + Vite + Tailwind
frontend using that project's established patterns (functional components, Tailwind
utility classes / the `@layer components` helpers in `index.css`, the existing `api.ts`
and WebSocket flow). The data shapes are already defined in the repo — reuse them.

### ⚠️ Prototype-only scaffolding (do NOT ship)
The prototype has a **top bar** used purely for review. It is not part of the real app:
- The screen nav (`Login · Empty · Main · Queue · Completed · Components`) — lets a
  reviewer jump between screens/states. The real app is a single page (`App.tsx`) that
  is the **Main** screen, gated by **Login**.
- The **Accent A/B** swatches — were for comparing two accent directions. **The chosen
  accent is Cyan (`#00e0c6`).** Magenta is dropped; ignore the toggle.
- The **Desktop/Mobile** toggle — just constrains the preview width to demonstrate the
  responsive layout. The real app is naturally responsive (see Responsive Behavior).

The **Components** screen is a developer reference (a component sheet), not an app route.

## Fidelity
**High-fidelity.** Final colors, typography, spacing, radii, shadows, and interaction
states are all specified below with exact values. Recreate pixel-faithfully using the
codebase's libraries. (Note: cover-art thumbnails referenced in copy are not drawn in the
prototype — the backend embeds covers in files; the UI does not need to render them
beyond the small source-icon tile, though showing a cover thumbnail per row would be a
welcome enhancement.)

---

## Design Tokens

### Color
| Token | Hex / value | Usage |
|---|---|---|
| `bg` | `#08090d` | Page background |
| `panel` | `#13151c` | Cards (paste box, login card, component cards) |
| `panel-alt` | `#11131a` | Queue rows, completed group cards |
| `inset` | `#0d0f14` | Inputs, textareas, selects, detected-row chips |
| `raised` | `#1b1e27` | Secondary button background |
| `border` | `rgba(255,255,255,0.07)` | Default panel/row border |
| `border-strong` | `rgba(255,255,255,0.10)` – `0.14` | Inputs, secondary/ghost buttons |
| `text` | `#e9ebf2` | Primary text |
| `text-2` | `#c3c8d4` / `#d4d8e0` | Secondary text, body |
| `muted` | `#9298a6` | Sub-labels, descriptions |
| `faint` | `#7e8493` / `#6a6f7c` / `#5f6573` / `#4f5562` | Mono labels, meta, footnotes (decreasing prominence) |
| **`accent`** | **`#00e0c6`** (cyan) | Primary buttons, focus rings, active progress, links, active nav |
| `on-accent` | `#08090d` | Text/icon on accent fills |
| `accent-tint` | `rgba(0,224,198,0.13–0.16)` | Accent badge/nav backgrounds |
| `accent-glow` | `color-mix(in srgb, #00e0c6 N%, transparent)` | Button + active-row glows |

### Source colors (fixed brand — do not change)
| Source | Color | Tint background |
|---|---|---|
| SoundCloud | `#ff7a2f` | `rgba(255,122,47,0.14)` |
| Spotify | `#1ed760` | `rgba(30,215,96,0.14)` |

### Status colors (one per `JobStatus`)
| Status | Color | Tint background |
|---|---|---|
| `queued` | `#9aa0b0` | `rgba(154,160,176,0.13)` |
| `downloading` | `#00e0c6` (accent) | `rgba(0,224,198,0.15)` |
| `converting` | `#f4a63a` (amber) | `rgba(244,166,58,0.15)` |
| `done` | `#2fe0a6` (mint) | `rgba(47,224,166,0.15)` |
| `failed` | `#ff5d73` (red) | `rgba(255,93,115,0.15)` |

### Typography
- **Space Grotesk** (Google Fonts, weights 400/500/600/700) — all UI text, headings,
  body, button labels. Replaces the repo's current `Inter`.
- **JetBrains Mono** (weights 400/500/600) — technical labels, status badges, source
  chips, URLs, file meta, counts, footnotes. (Repo already loads this.)
- Scale: screen title `23px / 600 / -0.02em`; login wordmark `26px / 600`; body `13–14px`;
  row title `14px / 500`; mono section labels `10–11px / 500`, `letter-spacing 0.12–0.16em`,
  `text-transform: uppercase`; status badge `10–11px / 500`; meta/footnotes `10–11px`.

### Radius
Pills/badges/chips `999px` · panels `12–14px` · inputs/buttons/selects `8–9px` ·
source-icon tile `9px` · accent swatch `5px`.

### Shadow / glow
- Panel: `0 20px 50px -30px rgba(0,0,0,0.7)` (login card uses `-28px / 0.8`).
- Primary button: `0 8px 26px -8px color-mix(in srgb, #00e0c6 75%, transparent)`;
  hover `filter: brightness(1.08)`.
- Active (downloading) queue row: border `rgba(0,224,198,0.28)` +
  `box-shadow: 0 0 0 1px rgba(0,224,198,0.12), 0 6px 26px -10px rgba(0,224,198,0.5)`.
- Progress fill: `box-shadow: 0 0 10px -1px <bar-color>`.
- Status/source dots: `box-shadow: 0 0 8px <color>` (live "glow dot").

### Spacing
Screen padding `30px` top / `90px` bottom / `6px` sides; content `max-width: 880px`
centered (`960px` for the component sheet). Panel padding `18px`. Queue/completed row
padding `14–15px`. Gaps: nav `4px`, options grid `11px`, detected list `7px`, queue list
`9px`, completed groups `14px`.

### Background texture (page-level, behind everything, `pointer-events:none`)
1. **Grid:** two 1px line gradients at `rgba(255,255,255,0.02)`, `background-size: 52px 52px`,
   masked with `radial-gradient(130% 90% at 50% -10%, #000 25%, transparent 78%)` so it
   fades out toward the bottom.
2. **Accent glow:** a blurred radial (`820×480px`, `blur(50px)`) pinned top-center,
   `radial-gradient(circle, color-mix(in srgb, #00e0c6 20%, transparent), transparent 62%)`,
   animated `glowpulse 7s ease-in-out infinite` (opacity 0.5↔0.95).

### Animations (`@keyframes`)
| Name | Def | Used by | Duration |
|---|---|---|---|
| `eq` | `0%,100%{scaleY(.3)} 50%{scaleY(1)}` | 3-bar equalizer inside the *Downloading* badge | `0.8s` infinite, bars staggered `0 / .15s / .3s`, `transform-origin:bottom` |
| `wave` | `0%,100%{scaleY(.25)} 50%{scaleY(1)}` | Login + empty-state decorative waveform (13 bars) | `0.9–1.5s`, staggered per bar |
| `shim` | `0%{translateX(-120%)} 100%{translateX(320%)}` | Shimmer sweep over the *Converting* progress bar | `1.3s` linear infinite |
| `glowpulse` | opacity `.5↔.95` | Background accent glow | `7s` |
| `blink` | opacity `1↔.25` | The dot inside the *Queued* badge | `1.4s` |

---

## Screens / Views

### 1. Login
- **Purpose:** Gate the app. Backend uses HTTP Basic Auth (`APP_USERNAME` / `APP_PASSWORD`);
  this is a styled login surface that captures and stores credentials for the session
  (or simply triggers the browser Basic Auth flow — match the repo's chosen approach).
- **Layout:** Full-height centered column, `max-width: 380px`.
  - Decorative animated waveform (13 cyan bars, `wave` animation) — `height: 42px`, centered.
  - Wordmark `music-dl` (`-dl` in accent), JetBrains Mono `26px`, + subtitle
    "Private SoundCloud & Spotify downloader. Sign in to continue." (`13px`, `muted`).
  - Card (`panel`, radius `14px`, padding `22px`, panel shadow) containing:
    - `Username` mono label → text input (default shown: `dj_max`).
    - `Password` mono label → password input.
    - Inputs: `inset` bg, `border-strong`, radius `9px`, padding `12px 14px`, `14px` text.
      **Focus:** `border-color: #00e0c6` + `box-shadow: 0 0 0 3px rgba(0,224,198,0.18)`.
    - Primary button **"Sign in →"**, full width, height `46px`, accent fill, on-accent text.
  - Footnote (mono `10px`, faint): `basic auth · private instance · tailscale only`.

### 2. Main (the core — this is `App.tsx`)
- **Purpose:** Paste URLs, pick options, start downloads, watch the queue, grab results.
- **Layout:** Single centered column `max-width: 880px`.
  - **Header row** (flex, space-between, wraps): title **"Drop your links"** (`23px/600`)
    + description "Paste one or more URLs — one per line. We detect the source
    automatically." On the right, a **live pill**: mint dot (glowing) + `live` (mono `11px`,
    color `#2fe0a6`, tint bg, `999px`). Maps to the repo's connection badge — show
    `live`/`offline` from the WebSocket connection state.
  - **Paste + options card** (`panel`, radius `14px`, padding `18px`, panel shadow):
    - **Textarea**: `inset` bg, `border-strong`, radius `11px`, padding `14px 15px`,
      JetBrains Mono `13px`, `line-height: 1.7`, `resize: vertical`, 4 rows. Focus ring as
      above. Placeholder shows two example URLs.
    - **Detected list** (renders when ≥1 non-empty line; see Interactions for detection):
      mono label `DETECTED · <count>` then one row per URL — each row (`inset` bg,
      border, radius `9px`, padding `9px 12px`, flex, gap `11px`):
      - Source chip: dot + name (`SoundCloud` / `Spotify` / `Unknown`), mono `11px`, in
        the source color + tint, `999px`.
      - The URL (mono `12px`, `text-2`, truncated with ellipsis).
      - Kind label on the right (`TRACK` / `SET` / `PLAYLIST` / `ALBUM`), mono `10px`,
        uppercase, faint.
      - **Spotify rows only:** a small circular ⓘ button (italic serif "i", green outline)
        that toggles a tooltip — see Interactions / Spotify note.
    - **Options row** (`display:grid; grid-template-columns: repeat(auto-fit, minmax(150px,1fr)); gap:11px; align-items:end`):
      - **Format** select — label `FORMAT` (mono). Options: `MP3 · M4A · OPUS · FLAC · OGG · WAV`.
        Custom-styled select on `inset` bg, radius `9px`, padding `11px 32px 11px 13px`,
        with a `▾` chevron absolutely positioned right. (`config.formats`, default
        `config.default_format` = `mp3`.)
      - **Quality** select — label `QUALITY`. Options: `128k · 192k · 256k · 320k · Best / auto`.
        (`config.bitrates`, default `config.default_bitrate` = `320k`.)
      - **Download button** (primary, accent, height `42px`): label `↓ Download (<n>)`
        where n = number of detected (non-unknown) URLs; just `↓ Download` when none.
        Disabled when no valid URLs.
    - **Toggle row**: a custom switch + "Prefer SoundCloud **original file** when available"
      (the bold phrase in SoundCloud orange `#ff7a2f`). Switch: track `40×23px`, `999px`;
      OFF track `#2a2e39`, ON track `#ff7a2f`; knob `17px` white circle, translateX
      `0→17px`, `transition: transform .2s`. Maps to `DownloadOptions.soundcloud_original`.
    - **Spotify info banner** (renders when any detected URL is Spotify): green-tinted
      box (`rgba(30,215,96,0.07)` bg, `rgba(30,215,96,0.18)` border, radius `9px`,
      padding `10px 12px`), ⓘ glyph + text: "Spotify links are matched to audio on
      **YouTube** — metadata & cover come from Spotify, bitrate is capped (~128–256k).
      FLAC won't be true lossless." (Matches the repo's existing spotify-config warning
      slot; merge with the `!config.spotify_configured` warning the repo already shows.)
  - **Queue section** (renders when jobs exist): mono header `QUEUE` + counts line
    `<q> queued · <a> active · <d> done · <f> failed` (faint, right-aligned). Then the
    list of queue rows (see Queue screen for the row spec). This is the live
    `Object.values(jobs)` from the existing App state, sorted newest-first.
  - **Completed section** (renders when finished files exist): mono header `COMPLETED` +
    a ghost **"⤓ Download all (.zip)"** button. Then completed groups (see Completed screen).
    Replaces / supersedes the repo's current `FileBrowser` flat list.

### 3. Empty state
The Main layout with no jobs and an empty textarea. The paste card shows a dashed-border
drop zone (`inset` bg, `1px dashed rgba(255,255,255,0.14)`, radius `11px`, padding
`40px 20px`, centered): faded waveform, "Nothing queued yet", a mono hint
`soundcloud.com/… · open.spotify.com/…`, and a secondary button "+ Paste example links".
No queue or completed sections render.

### 4. Queue — all status states
The queue is a vertical list (`gap: 9px`). Each **row** (`panel-alt` bg, border, radius
`12px`, padding `14px 15px`):
- **Top line** (flex, gap `12px`, align top):
  - **Source icon tile** `34×34px`, radius `9px`, source-tint bg, source-color mono
    initials (`SC` / `SP`).
  - **Title** (`14px/500`, truncated) + inline **status badge** (mono `10px`, `999px`,
    status color on status tint, padding `3px 9px`):
    - `queued` — leading **blinking dot** (`blink`) + "Queued".
    - `downloading` — leading **3-bar EQ** (`eq`, staggered) + "Downloading".
    - `converting` — "Converting" (no glyph).
    - `done` — "Done".
    - `failed` — "Failed".
  - If the job has a playlist: a sub-line `↳ in "<playlist>"` (`12px`, faint, truncated).
  - **Right-side action:** `done` → ghost **"↓ Save"** link (height `30px`); `failed` →
    **"↻ Retry"** button (red-tinted).
- **Progress bar** (only for `downloading` + `converting`): track `height: 4px`,
  `999px`, `rgba(255,255,255,0.07)`; fill width = `max(5, progress)%` (converting pins
  to 100%), fill color = accent for downloading / amber for converting, with the
  `0 0 10px -1px` glow; **converting** adds the `shim` shimmer sweep overlay. To the
  right, a mono value: `<n>%` while downloading, `processing…` while converting.
- **Spotify + done:** a faint mono line `↳ audio matched from YouTube · bitrate capped by source`.
- **Failed:** an error box (red-tint bg `rgba(255,93,115,0.08)`, red border, radius `8px`,
  padding `9px 11px`): `⚠` + `job.error` text. Example error used:
  *"Download disabled by uploader (HTTP 403). Add SOUNDCLOUD_AUTH_TOKEN in .env to fetch
  original / private files."*
- **Active rows** (downloading) get the accent border + glow described in Shadow/glow.

Maps to the repo's `JobRow.tsx` — extend it to cover all five states, the EQ/blink badge
glyphs, the converting shimmer, the YouTube note, and the Retry action.

### 5. Completed — grouped by playlist
Vertical list of **group cards** (`panel-alt` bg, border, radius `12px`, overflow hidden):
- **Group header** (padding `12px 15px`, bottom border, faint bg): source chip +
  group/playlist name (`14px/600`, truncated) + count (`<n> tracks`, mono, faint) + a
  small ghost **".zip"** button (per-group download).
- **Track rows** (padding `10–11px 15px`, bottom border, hover bg `rgba(255,255,255,0.02)`):
  source-color dot + title (`13.5px`, truncated) + (Spotify tracks: sub-line
  `↳ from YouTube match`, mono `10px`) + file meta on the right (mono `10.5px`, faint,
  e.g. `FLAC · 320k · 31.2 MB`) + a `↓` icon button (`30×30px`, bordered, accent on hover).
- A screen-level primary **"⤓ Download all (.zip)"** button sits in the Completed header.

Example groups used: "Afro House — Sunset Sessions" (SoundCloud, 3), "Melodic Techno
Selects" (Spotify, 3), "Singles" (mixed, 1). Newly finished sim downloads append to a
"Just downloaded" group at the top. In the real app, group by `Job.playlist` (null →
"Singles") and read files via the existing files API (`api.fileUrl`, zip endpoint).

### 6. Component sheet (dev reference only — not an app route)
A grid of labeled cards demonstrating: Buttons (primary / secondary / ghost / disabled),
Source chips, all five Status badges, Progress bars (30% / 72% / converting-shimmer),
Toggle + dropdown, URL input, and the Spotify→YouTube info element. Use this as the
single source of truth for each component's exact styling.

---

## Interactions & Behavior
- **Source auto-detection (live, on every keystroke):** split the textarea on newlines,
  trim, drop blanks. For each line classify by host substring:
  `soundcloud.com` / `snd.sc` → SoundCloud; `spotify.com` / `spotify.link` → Spotify;
  else Unknown. **Kind label:** Spotify → `Playlist` if URL contains `/playlist/`,
  `Album` if `/album/`, `Track` if `/track/`; SoundCloud → `Set` if `/sets/`, else `Track`.
  Render the detected list reactively. Only non-Unknown URLs count toward the Download
  count and are submitted.
- **Download:** submit the detected URLs + `{format, bitrate, soundcloud_original}` via
  `api.submit(...)` (existing). Jobs enter the queue as `queued`. Clear the textarea.
- **Live progress:** in the real app, status + `progress` come over the WebSocket
  (`openProgressSocket`) / `GET /api/jobs` fallback — exactly as the repo does today.
  (The prototype fakes this with a 620ms tick advancing `queued → downloading →
  converting → done`, ~16–30% per tick — for reference only; use the real WS.)
- **Retry (failed):** re-submit that job; in the prototype it flips the row back to
  `downloading`.
- **Spotify ⓘ tooltip:** clicking the ⓘ on a detected Spotify row toggles a small popover
  (`#1b1e27` bg, border, radius `11px`, `236px` wide, shadow, positioned above-right):
  heading "Audio matched from YouTube" (green) + "Spotify can't be downloaded directly.
  We pull metadata + cover from Spotify and the closest audio from YouTube — so bitrate
  is capped (~128–256k)." Non-alarming, dismissible. Only one open at a time.
- **Save / download links:** `done` rows + completed tracks link to the file
  (`api.fileUrl(output_path)`); "Download all (.zip)" hits the zip endpoint.
- **Hover states:** primary button `brightness(1.08)`; ghost/secondary buttons lighten
  bg or shift border to accent; icon download buttons turn accent; completed track rows
  get a faint bg tint. **Focus:** inputs/textareas/selects get accent border + 3px
  accent-tint ring.

## State Management
Reuse the repo's existing state model (`App.tsx`):
- `config: AppConfig | null`, `jobs: Record<string, Job>`, `connected: boolean`,
  `error: string | null`, plus a files/completed refresh trigger.
- Local form state (in `UrlForm`): `text`, `format`, `bitrate`, `soundcloud_original`,
  `busy`. **Add:** derived `detected[]` from `text` (see detection above), and an
  `openTip` id for the Spotify tooltip.
- `Job` already carries everything the UI needs: `source`, `title`, `playlist`,
  `status`, `progress`, `audio_source` (the YouTube provider for the note),
  `output_path`, `error`. No new backend fields required.
- Completed grouping is a pure derivation over finished jobs/files by `playlist`.

## Responsive Behavior
Fully responsive desktop + mobile from one layout (the prototype's Desktop/Mobile toggle
just changes the container width):
- Content column is `max-width: 880px`, fluid below that.
- Options row uses `grid-template-columns: repeat(auto-fit, minmax(150px, 1fr))` — it
  reflows from one row on desktop to stacked on narrow screens with **no media queries**.
- Completed/component grids use `repeat(auto-fit, minmax(260–280px, 1fr))`.
- Header rows, nav, and chip rows use `flex-wrap: wrap`.
- Touch targets ≥ 40px (buttons 40–46px; switch 40×23; icon buttons 28–30px).
- Implement with Tailwind responsive utilities or the same auto-fit grid approach.

## Tailwind / setup notes (for this repo)
- Swap the body font from `Inter` to **Space Grotesk**; keep **JetBrains Mono** for the
  `font-mono` stack. Update the Google Fonts `@import` in `frontend/src/index.css`.
- Extend `tailwind.config.js` `theme.colors`: set `accent.DEFAULT` to `#00e0c6`
  (drop the old `#ff5722`), keep `soundcloud: #ff5500` (or use the design's `#ff7a2f`
  for better contrast on dark) and `spotify: #1db954` (design uses `#1ed760`), and add
  the status colors above. Keep the `ink` scale or replace with the bg/panel/inset values.
- The existing `@layer components` helpers (`.card`, `.btn-primary`, `.field`, `.badge`)
  map cleanly onto this design — update their values to the tokens above.
- Replace the current pink/orange radial body gradients with the grid + cyan glow texture.

## Assets
No raster assets, icons, or images are required. All glyphs are Unicode characters
(`▸ ↓ ↻ ⤓ ↳ ✓ ⚠ ▾ i`) and CSS-drawn shapes (dots, bars, waveform). Fonts load from Google
Fonts (Space Grotesk, JetBrains Mono). Cover art is embedded into files by the backend;
the UI optionally could render a small cover thumbnail per row (not in this prototype).

## Files
- `screenshots/` — rendered reference images (cyan, the chosen accent):
  `01-login`, `02-main`, `03-main-queue`, `04-queue-states` (all five statuses),
  `05-completed`, `06-components`, `07-empty`, `08-mobile-main`, `09-mobile-queue`.
- `Music-dl.dc.html` — the full interactive design prototype (all screens + states).
  Open it in a browser to inspect every state, the component sheet, and the
  paste → queue → completed flow. Inline styles in this file are the exact spec.
- Target repo to implement in: `maxloeh/song-downloader` → `frontend/src/`
  (`App.tsx`, `components/UrlForm.tsx`, `components/JobRow.tsx`, a new `Login`, a
  completed/results section, `index.css`, `tailwind.config.js`). Reuse `types.ts` and
  `api.ts` unchanged.
