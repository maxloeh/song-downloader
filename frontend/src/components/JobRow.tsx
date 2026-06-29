import { api } from "../api";
import { FONT_MONO, SOURCE, STATUS, T } from "../theme";
import type { Job } from "../types";

interface Props {
  job: Job;
  onRetry: (job: Job) => void;
  onDismiss: (job: Job) => void;
}

export default function JobRow({ job, onRetry, onDismiss }: Props) {
  const s = SOURCE[job.source] ?? SOURCE.unknown;
  const st = STATUS[job.status] ?? STATUS.queued;
  const isDownloading = job.status === "downloading";
  const isConverting = job.status === "converting";
  const showBar = isDownloading || isConverting;
  const barColor = isConverting ? STATUS.converting.color : STATUS.downloading.color;
  const barPct = isConverting ? 100 : Math.max(5, job.progress);
  const pctLabel = isConverting ? "processing…" : `${Math.round(job.progress)}%`;
  const active = isDownloading || isConverting;
  const title = job.title || job.url;

  const rowStyle: React.CSSProperties = {
    background: T.panelAlt,
    border: active ? "1px solid rgba(0,224,198,0.28)" : `1px solid ${T.border}`,
    borderRadius: 12,
    padding: "14px 15px",
    boxShadow: active
      ? "0 0 0 1px rgba(0,224,198,0.12), 0 6px 26px -10px rgba(0,224,198,0.5)"
      : "none",
  };

  return (
    <div style={rowStyle}>
      <div style={{ display: "flex", alignItems: "flex-start", gap: 12 }}>
        {job.artwork_url ? (
          <img
            src={job.artwork_url}
            alt=""
            loading="lazy"
            style={{
              flexShrink: 0,
              width: 34,
              height: 34,
              borderRadius: 9,
              objectFit: "cover",
              background: s.bg,
            }}
            onError={(e) => {
              (e.currentTarget as HTMLImageElement).style.display = "none";
            }}
          />
        ) : (
          <span
            style={{
              flexShrink: 0,
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              width: 34,
              height: 34,
              borderRadius: 9,
              background: s.bg,
              color: s.color,
              fontFamily: FONT_MONO,
              fontSize: 11,
              fontWeight: 600,
            }}
          >
            {s.initials}
          </span>
        )}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            <span
              style={{
                fontSize: 14,
                fontWeight: 500,
                color: T.text,
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
                maxWidth: "100%",
              }}
              title={title}
            >
              {title}
            </span>
            <span
              style={{
                flexShrink: 0,
                display: "inline-flex",
                alignItems: "center",
                gap: 6,
                fontFamily: FONT_MONO,
                fontSize: 10,
                fontWeight: 500,
                letterSpacing: "0.04em",
                color: st.color,
                background: st.bg,
                borderRadius: 999,
                padding: "3px 9px",
              }}
            >
              {isDownloading && (
                <span style={{ display: "inline-flex", alignItems: "flex-end", gap: 1.5, height: 9 }}>
                  {[0, 0.15, 0.3].map((delay) => (
                    <i
                      key={delay}
                      style={{
                        width: 2,
                        height: "100%",
                        background: st.color,
                        transformOrigin: "bottom",
                        animation: `eq 0.8s ease-in-out infinite ${delay}s`,
                      }}
                    />
                  ))}
                </span>
              )}
              {job.status === "queued" && (
                <span
                  style={{
                    width: 5,
                    height: 5,
                    borderRadius: "50%",
                    background: st.color,
                    animation: "blink 1.4s ease-in-out infinite",
                  }}
                />
              )}
              {st.label}
            </span>
          </div>
          {job.playlist && (
            <div
              style={{
                marginTop: 3,
                fontSize: 12,
                color: T.faint2,
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
            >
              ↳ in “{job.playlist}”
            </div>
          )}
        </div>

        {job.status === "done" && job.output_path && (
          <a
            href={api.fileUrl(job.output_path)}
            style={{
              flexShrink: 0,
              display: "inline-flex",
              alignItems: "center",
              gap: 5,
              height: 30,
              padding: "0 12px",
              border: `1px solid ${T.borderStrong}`,
              borderRadius: 8,
              background: "rgba(255,255,255,0.04)",
              color: T.text2,
              fontSize: 12,
              textDecoration: "none",
            }}
          >
            ↓ Save
          </a>
        )}
        {job.status === "failed" && (
          <div style={{ flexShrink: 0, display: "flex", gap: 6 }}>
            <button
              type="button"
              onClick={() => onRetry(job)}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 5,
                height: 30,
                padding: "0 12px",
                border: "1px solid rgba(255,93,115,0.3)",
                borderRadius: 8,
                background: "rgba(255,93,115,0.08)",
                color: "#ff5d73",
                fontSize: 12,
                cursor: "pointer",
              }}
            >
              ↻ Retry
            </button>
            <button
              type="button"
              onClick={() => onDismiss(job)}
              title="Dismiss"
              style={{
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                width: 30,
                height: 30,
                border: `1px solid ${T.borderStrong}`,
                borderRadius: 8,
                background: "rgba(255,255,255,0.04)",
                color: T.muted,
                fontSize: 13,
                cursor: "pointer",
              }}
            >
              ✕
            </button>
          </div>
        )}
      </div>

      {showBar && (
        <div style={{ marginTop: 11, display: "flex", alignItems: "center", gap: 10 }}>
          <div
            style={{
              flex: 1,
              height: 4,
              borderRadius: 999,
              background: "rgba(255,255,255,0.07)",
              overflow: "hidden",
              position: "relative",
            }}
          >
            <div
              style={{
                height: "100%",
                borderRadius: 999,
                width: `${barPct}%`,
                background: barColor,
                boxShadow: `0 0 10px -1px ${barColor}`,
                transition: "width 0.4s ease",
                position: "relative",
                overflow: "hidden",
              }}
            >
              {isConverting && (
                <span
                  style={{
                    position: "absolute",
                    inset: 0,
                    background:
                      "linear-gradient(90deg, transparent, rgba(255,255,255,0.55), transparent)",
                    animation: "shim 1.3s linear infinite",
                  }}
                />
              )}
            </div>
          </div>
          <span
            style={{
              flexShrink: 0,
              fontFamily: FONT_MONO,
              fontSize: 11,
              color: T.muted,
              minWidth: 64,
              textAlign: "right",
            }}
          >
            {pctLabel}
          </span>
        </div>
      )}

      {job.audio_source?.toLowerCase().includes("youtube") && job.status === "done" && (
        <div style={{ marginTop: 9, fontFamily: FONT_MONO, fontSize: 10.5, color: T.faint2 }}>
          ↳ {job.source === "soundcloud" ? "SoundCloud unavailable — matched from" : "audio matched from"}{" "}
          YouTube · bitrate capped by source
        </div>
      )}

      {job.status === "failed" && job.error && (
        <div
          style={{
            marginTop: 10,
            display: "flex",
            gap: 8,
            alignItems: "flex-start",
            background: "rgba(255,93,115,0.08)",
            border: "1px solid rgba(255,93,115,0.2)",
            borderRadius: 8,
            padding: "9px 11px",
          }}
        >
          <span style={{ color: "#ff5d73", flexShrink: 0, fontSize: 13, lineHeight: 1.3 }}>⚠</span>
          <span style={{ fontSize: 12, lineHeight: 1.5, color: "#e3a3ac" }}>{job.error}</span>
        </div>
      )}
    </div>
  );
}
