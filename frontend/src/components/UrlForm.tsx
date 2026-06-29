import { useMemo, useState } from "react";
import { FONT_MONO, SOURCE, T } from "../theme";
import type { AppConfig, DownloadOptions } from "../types";

interface Props {
  config: AppConfig;
  spotifyConfigured: boolean;
  onSubmit: (urls: string[], options: DownloadOptions) => Promise<void>;
}

type DetectedSource = "soundcloud" | "spotify" | "unknown";

interface Detected {
  url: string;
  source: DetectedSource;
  display: string;
  kind: string;
}

const EXAMPLE_URLS =
  "https://soundcloud.com/artist/track\nhttps://open.spotify.com/playlist/37i9dQZF1DX0XUsuxWHRQd";

function detect(line: string): Detected {
  const url = line.trim();
  const lower = url.toLowerCase();
  let source: DetectedSource = "unknown";
  if (lower.includes("soundcloud.com") || lower.includes("snd.sc")) source = "soundcloud";
  else if (lower.includes("spotify.com") || lower.includes("spotify.link")) source = "spotify";

  let kind = "Track";
  if (source === "spotify") {
    kind = lower.includes("/playlist/") ? "Playlist" : lower.includes("/album/") ? "Album" : "Track";
  } else if (source === "soundcloud") {
    kind = lower.includes("/sets/") ? "Set" : "Track";
  }

  const display = url.replace(/^https?:\/\//, "").replace(/^www\./, "").split("?")[0];
  return { url, source, display, kind };
}

const monoLabel: React.CSSProperties = {
  fontFamily: FONT_MONO,
  fontSize: 10,
  letterSpacing: "0.12em",
  textTransform: "uppercase",
  color: T.faint,
};

export default function UrlForm({ config, spotifyConfigured, onSubmit }: Props) {
  const [text, setText] = useState("");
  const [format, setFormat] = useState(config.default_format);
  const [bitrate, setBitrate] = useState(config.default_bitrate);
  const [scOriginal, setScOriginal] = useState(false);
  const [ytFallback, setYtFallback] = useState(true);
  const [busy, setBusy] = useState(false);
  const [openTip, setOpenTip] = useState<number | null>(null);

  const detected = useMemo(
    () =>
      text
        .split(/\n/)
        .map((l) => l.trim())
        .filter(Boolean)
        .map(detect),
    [text],
  );
  const valid = detected.filter((d) => d.source !== "unknown");
  const hasSpotify = detected.some((d) => d.source === "spotify");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!valid.length || busy) return;
    setBusy(true);
    try {
      await onSubmit(
        valid.map((d) => d.url),
        { format, bitrate, soundcloud_original: scOriginal, youtube_fallback: ytFallback },
      );
      setText("");
    } finally {
      setBusy(false);
    }
  }

  const bitrateLabel = (b: string) => (b === "best" ? "Best / auto" : b);

  return (
    <form
      onSubmit={handleSubmit}
      style={{
        background: T.panel,
        border: `1px solid ${T.border}`,
        borderRadius: 14,
        padding: 18,
        boxShadow: "0 20px 50px -30px rgba(0,0,0,0.7)",
      }}
    >
      <textarea
        className="dc-textarea"
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={4}
        spellCheck={false}
        placeholder={EXAMPLE_URLS}
        style={{
          width: "100%",
          resize: "vertical",
          background: T.inset,
          border: `1px solid ${T.borderStrong}`,
          borderRadius: 11,
          color: T.text,
          padding: "14px 15px",
          fontFamily: FONT_MONO,
          fontSize: 13,
          lineHeight: 1.7,
          outline: "none",
        }}
      />

      {/* Detected list */}
      {detected.length > 0 && (
        <div style={{ marginTop: 14 }}>
          <div style={{ ...monoLabel, marginBottom: 9 }}>Detected · {detected.length}</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 7 }}>
            {detected.map((d, i) => {
              const s = SOURCE[d.source];
              return (
                <div
                  key={i}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 11,
                    background: T.inset,
                    border: `1px solid ${T.border}`,
                    borderRadius: 9,
                    padding: "9px 12px",
                  }}
                >
                  <span
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: 6,
                      flexShrink: 0,
                      fontFamily: FONT_MONO,
                      fontSize: 11,
                      fontWeight: 500,
                      color: s.color,
                      background: s.bg,
                      borderRadius: 999,
                      padding: "4px 9px",
                    }}
                  >
                    <span
                      style={{ width: 6, height: 6, borderRadius: "50%", background: s.color }}
                    />
                    {s.name}
                  </span>
                  <span
                    style={{
                      flex: 1,
                      minWidth: 0,
                      fontFamily: FONT_MONO,
                      fontSize: 12,
                      color: T.text2,
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                    title={d.url}
                  >
                    {d.display}
                  </span>
                  <span
                    style={{
                      flexShrink: 0,
                      fontFamily: FONT_MONO,
                      fontSize: 10,
                      letterSpacing: "0.06em",
                      color: T.faint2,
                      textTransform: "uppercase",
                    }}
                  >
                    {d.kind}
                  </span>
                  {d.source === "spotify" && (
                    <div style={{ position: "relative", flexShrink: 0 }}>
                      <button
                        type="button"
                        onClick={() => setOpenTip(openTip === i ? null : i)}
                        style={{
                          display: "inline-flex",
                          alignItems: "center",
                          justifyContent: "center",
                          width: 18,
                          height: 18,
                          borderRadius: "50%",
                          border: "1px solid rgba(30,215,96,0.4)",
                          background: "rgba(30,215,96,0.1)",
                          color: "#1ed760",
                          fontSize: 11,
                          fontStyle: "italic",
                          fontFamily: "Georgia, serif",
                          cursor: "pointer",
                          lineHeight: 1,
                        }}
                      >
                        i
                      </button>
                      {openTip === i && (
                        <div
                          style={{
                            position: "absolute",
                            bottom: "150%",
                            right: -4,
                            width: 236,
                            zIndex: 30,
                            background: T.raised,
                            border: `1px solid ${T.borderStronger}`,
                            borderRadius: 11,
                            padding: "11px 13px",
                            fontSize: 12,
                            lineHeight: 1.55,
                            color: T.text2,
                            boxShadow: "0 16px 40px -10px rgba(0,0,0,0.7)",
                          }}
                        >
                          <span
                            style={{
                              display: "block",
                              color: "#1ed760",
                              fontWeight: 600,
                              marginBottom: 4,
                              fontSize: 11,
                            }}
                          >
                            Audio matched from YouTube
                          </span>
                          Spotify can't be downloaded directly. We pull metadata + cover from
                          Spotify and the closest audio from YouTube — so bitrate is capped
                          (~128–256k).
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Options row */}
      <div
        style={{
          marginTop: 16,
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
          gap: 11,
          alignItems: "end",
        }}
      >
        <label style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <span style={monoLabel}>Format</span>
          <SelectField value={format} onChange={setFormat}>
            {config.formats.map((f) => (
              <option key={f} value={f}>
                {f.toUpperCase()}
              </option>
            ))}
          </SelectField>
        </label>
        <label style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <span style={monoLabel}>Quality</span>
          <SelectField value={bitrate} onChange={setBitrate}>
            {config.bitrates.map((b) => (
              <option key={b} value={b}>
                {bitrateLabel(b)}
              </option>
            ))}
          </SelectField>
        </label>
        <button
          type="submit"
          disabled={!valid.length || busy}
          style={{
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 8,
            height: 42,
            padding: "0 20px",
            border: "none",
            borderRadius: 9,
            background: T.accent,
            color: T.onAccent,
            fontWeight: 600,
            fontSize: 14,
            cursor: valid.length && !busy ? "pointer" : "not-allowed",
            opacity: valid.length && !busy ? 1 : 0.5,
            boxShadow: "0 8px 26px -8px color-mix(in srgb, #00e0c6 75%, transparent)",
          }}
        >
          {busy ? "Queuing…" : `↓ Download${valid.length ? ` (${valid.length})` : ""}`}
        </button>
      </div>

      {/* Toggles */}
      <div style={{ marginTop: 15, display: "flex", flexDirection: "column", gap: 11 }}>
        <Toggle on={scOriginal} onColor="#ff7a2f" onToggle={() => setScOriginal((v) => !v)}>
          Prefer SoundCloud{" "}
          <span style={{ fontWeight: 600, color: "#ff7a2f" }}>original file</span> when available
        </Toggle>
        <Toggle on={ytFallback} onColor={T.accent} onToggle={() => setYtFallback((v) => !v)}>
          When SoundCloud can't serve a track, fall back to a{" "}
          <span style={{ fontWeight: 600, color: T.accent }}>YouTube match</span>
        </Toggle>
      </div>

      {/* Spotify / YouTube source banner */}
      {(hasSpotify || !spotifyConfigured) && (
        <div
          style={{
            marginTop: 13,
            display: "flex",
            gap: 9,
            alignItems: "flex-start",
            background: "rgba(30,215,96,0.07)",
            border: "1px solid rgba(30,215,96,0.18)",
            borderRadius: 9,
            padding: "10px 12px",
          }}
        >
          <span
            style={{
              flexShrink: 0,
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              width: 16,
              height: 16,
              borderRadius: "50%",
              background: "rgba(30,215,96,0.18)",
              color: "#1ed760",
              fontSize: 10,
              fontStyle: "italic",
              fontFamily: "Georgia, serif",
              marginTop: 1,
            }}
          >
            i
          </span>
          <span style={{ fontSize: 12, lineHeight: 1.5, color: "#9aa6a0" }}>
            Spotify links are matched to audio on <span style={{ color: "#1ed760" }}>YouTube</span>{" "}
            — metadata &amp; cover come from Spotify, bitrate is capped (~128–256k). FLAC won't be
            true lossless.
            {!spotifyConfigured && (
              <>
                {" "}
                <span style={{ color: "#f4a63a" }}>
                  No Spotify API credentials set — connect Spotify below for reliable results.
                </span>
              </>
            )}
          </span>
        </div>
      )}
    </form>
  );
}

function Toggle({
  on,
  onColor,
  onToggle,
  children,
}: {
  on: boolean;
  onColor: string;
  onToggle: () => void;
  children: React.ReactNode;
}) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
      <button
        type="button"
        onClick={onToggle}
        aria-pressed={on}
        style={{
          position: "relative",
          width: 40,
          height: 23,
          borderRadius: 999,
          border: "none",
          cursor: "pointer",
          background: on ? onColor : "#2a2e39",
          transition: "background 0.2s",
          flexShrink: 0,
        }}
      >
        <span
          style={{
            position: "absolute",
            top: 3,
            left: 3,
            width: 17,
            height: 17,
            borderRadius: "50%",
            background: "#fff",
            transform: `translateX(${on ? 17 : 0}px)`,
            transition: "transform 0.2s",
          }}
        />
      </button>
      <span style={{ fontSize: 13, color: T.text2 }}>{children}</span>
    </div>
  );
}

function SelectField({
  value,
  onChange,
  children,
}: {
  value: string;
  onChange: (v: string) => void;
  children: React.ReactNode;
}) {
  return (
    <div style={{ position: "relative" }}>
      <select
        className="dc-select"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        style={{
          width: "100%",
          background: T.inset,
          border: `1px solid ${T.borderStrong}`,
          borderRadius: 9,
          color: T.text,
          padding: "11px 32px 11px 13px",
          fontSize: 13,
          fontWeight: 500,
          outline: "none",
          cursor: "pointer",
        }}
      >
        {children}
      </select>
      <span
        style={{
          position: "absolute",
          right: 12,
          top: "50%",
          transform: "translateY(-50%)",
          pointerEvents: "none",
          color: T.faint,
          fontSize: 10,
        }}
      >
        ▾
      </span>
    </div>
  );
}
