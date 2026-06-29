/**
 * Design tokens from the music-dl UI handoff (chosen accent: cyan #00e0c6).
 * Kept as plain constants so per-source / per-status colors can be applied as
 * inline styles, which is the most faithful way to hit the exact spec values.
 */

export const T = {
  bg: "#08090d",
  panel: "#13151c",
  panelAlt: "#11131a",
  inset: "#0d0f14",
  raised: "#1b1e27",
  border: "rgba(255,255,255,0.07)",
  borderStrong: "rgba(255,255,255,0.10)",
  borderStronger: "rgba(255,255,255,0.14)",
  text: "#e9ebf2",
  text2: "#c3c8d4",
  text3: "#d4d8e0",
  muted: "#9298a6",
  faint: "#7e8493",
  faint2: "#6a6f7c",
  faint3: "#5f6573",
  faint4: "#4f5562",
  accent: "#00e0c6",
  onAccent: "#08090d",
} as const;

export interface SourceStyle {
  color: string;
  bg: string;
  name: string;
  initials: string;
}

export const SOURCE: Record<"soundcloud" | "spotify" | "unknown", SourceStyle> = {
  soundcloud: { color: "#ff7a2f", bg: "rgba(255,122,47,0.14)", name: "SoundCloud", initials: "SC" },
  spotify: { color: "#1ed760", bg: "rgba(30,215,96,0.14)", name: "Spotify", initials: "SP" },
  unknown: { color: "#9298a6", bg: "rgba(146,152,166,0.12)", name: "Unknown", initials: "?" },
};

export interface StatusStyle {
  color: string;
  bg: string;
  label: string;
}

export const STATUS: Record<string, StatusStyle> = {
  queued: { color: "#9aa0b0", bg: "rgba(154,160,176,0.13)", label: "Queued" },
  downloading: { color: "#00e0c6", bg: "rgba(0,224,198,0.15)", label: "Downloading" },
  converting: { color: "#f4a63a", bg: "rgba(244,166,58,0.15)", label: "Converting" },
  done: { color: "#2fe0a6", bg: "rgba(47,224,166,0.15)", label: "Done" },
  failed: { color: "#ff5d73", bg: "rgba(255,93,115,0.15)", label: "Failed" },
};

export const FONT_MONO = "'JetBrains Mono', ui-monospace, monospace";

export function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB"];
  let v = bytes / 1024;
  let i = 0;
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024;
    i++;
  }
  return `${v.toFixed(1)} ${units[i]}`;
}
