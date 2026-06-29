import { useState } from "react";
import type { AppConfig, DownloadOptions } from "../types";

interface Props {
  config: AppConfig;
  onSubmit: (urls: string[], options: DownloadOptions) => Promise<void>;
}

export default function UrlForm({ config, onSubmit }: Props) {
  const [text, setText] = useState("");
  const [format, setFormat] = useState(config.default_format);
  const [bitrate, setBitrate] = useState(config.default_bitrate);
  const [scOriginal, setScOriginal] = useState(false);
  const [busy, setBusy] = useState(false);

  const urls = text
    .split(/\s+/)
    .map((u) => u.trim())
    .filter(Boolean);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!urls.length || busy) return;
    setBusy(true);
    try {
      await onSubmit(urls, {
        format,
        bitrate,
        soundcloud_original: scOriginal,
      });
      setText("");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="card p-5 sm:p-6">
      <label className="mb-2 block text-sm font-medium text-slate-300">
        Paste SoundCloud or Spotify links — one per line
      </label>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={4}
        spellCheck={false}
        placeholder={
          "https://soundcloud.com/artist/track\nhttps://open.spotify.com/playlist/…"
        }
        className="field w-full resize-y font-mono text-[13px] leading-relaxed"
      />

      <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-[1fr_1fr_auto]">
        <label className="flex flex-col gap-1.5">
          <span className="text-xs uppercase tracking-wide text-slate-400">Format</span>
          <select
            value={format}
            onChange={(e) => setFormat(e.target.value)}
            className="field"
          >
            {config.formats.map((f) => (
              <option key={f} value={f}>
                {f.toUpperCase()}
              </option>
            ))}
          </select>
        </label>

        <label className="flex flex-col gap-1.5">
          <span className="text-xs uppercase tracking-wide text-slate-400">Quality</span>
          <select
            value={bitrate}
            onChange={(e) => setBitrate(e.target.value)}
            className="field"
          >
            {config.bitrates.map((b) => (
              <option key={b} value={b}>
                {b === "best" ? "Best / auto" : b}
              </option>
            ))}
          </select>
        </label>

        <div className="flex items-end">
          <button type="submit" disabled={!urls.length || busy} className="btn-primary h-[42px] w-full sm:w-auto">
            {busy ? "Queuing…" : `Download${urls.length ? ` (${urls.length})` : ""}`}
          </button>
        </div>
      </div>

      <label className="mt-3 flex items-center gap-2.5 text-sm text-slate-300">
        <input
          type="checkbox"
          checked={scOriginal}
          onChange={(e) => setScOriginal(e.target.checked)}
          className="h-4 w-4 rounded border-white/20 bg-ink-800 accent-soundcloud"
        />
        Prefer SoundCloud <span className="font-medium">original file</span> when available
      </label>

      {!config.spotify_configured && (
        <p className="mt-3 rounded-lg border border-amber-500/20 bg-amber-500/10 px-3 py-2 text-xs text-amber-300">
          Spotify API credentials are not set — Spotify links use spotDL's limited
          no-API mode and may fail. Add <code>SPOTIFY_CLIENT_ID</code>/<code>SECRET</code> to <code>.env</code>.
        </p>
      )}
    </form>
  );
}
