import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { FONT_MONO, formatSize, SOURCE, T } from "../theme";
import type { FileItem, Job } from "../types";

interface Props {
  jobs: Job[];
  refreshKey: number;
}

interface Group {
  key: string;
  name: string;
  source: "soundcloud" | "spotify";
  playlist: string | null;
  tracks: { job: Job; meta: string }[];
}

const SINGLES = "Singles";

export default function CompletedSection({ jobs, refreshKey }: Props) {
  const [sizes, setSizes] = useState<Record<string, number>>({});

  useEffect(() => {
    let cancelled = false;
    api
      .listFiles()
      .then((files: FileItem[]) => {
        if (cancelled) return;
        const map: Record<string, number> = {};
        files.forEach((f) => (map[f.path] = f.size));
        setSizes(map);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [refreshKey]);

  const done = useMemo(
    () => jobs.filter((j) => j.status === "done" && j.output_path),
    [jobs],
  );

  const groups = useMemo<Group[]>(() => {
    const byKey = new Map<string, Group>();
    for (const job of done) {
      const playlist = job.playlist || null;
      const key = playlist ?? SINGLES;
      let g = byKey.get(key);
      if (!g) {
        g = {
          key,
          name: playlist ?? SINGLES,
          source: job.source,
          playlist,
          tracks: [],
        };
        byKey.set(key, g);
      }
      const ext = (job.output_path!.split(".").pop() || "").toUpperCase();
      const size = sizes[job.output_path!];
      const quality =
        job.source === "soundcloud" && job.options.soundcloud_original
          ? "orig"
          : job.source === "spotify"
            ? `~${job.options.bitrate}`
            : job.options.bitrate;
      const meta = [ext, quality, size != null ? formatSize(size) : null]
        .filter(Boolean)
        .join(" · ");
      g.tracks.push({ job, meta });
    }
    return Array.from(byKey.values());
  }, [done, sizes]);

  if (done.length === 0) return null;

  return (
    <section style={{ marginTop: 30 }}>
      <div
        style={{
          display: "flex",
          alignItems: "baseline",
          justifyContent: "space-between",
          gap: 12,
          marginBottom: 13,
          flexWrap: "wrap",
        }}
      >
        <h3
          style={{
            margin: 0,
            fontFamily: FONT_MONO,
            fontSize: 11,
            letterSpacing: "0.16em",
            textTransform: "uppercase",
            color: T.faint,
          }}
        >
          Completed
        </h3>
        <a href={api.zipUrl()} className="dc-ghost-btn" style={ghostBtn}>
          ⤓ Download all (.zip)
        </a>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        {groups.map((g) => {
          const s = SOURCE[g.source];
          return (
            <div
              key={g.key}
              style={{
                background: T.panelAlt,
                border: `1px solid ${T.border}`,
                borderRadius: 12,
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                  padding: "12px 15px",
                  borderBottom: "1px solid rgba(255,255,255,0.06)",
                  background: "rgba(255,255,255,0.015)",
                }}
              >
                <span
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 6,
                    fontFamily: FONT_MONO,
                    fontSize: 11,
                    fontWeight: 500,
                    color: s.color,
                    background: s.bg,
                    borderRadius: 999,
                    padding: "4px 9px",
                  }}
                >
                  <span style={{ width: 6, height: 6, borderRadius: "50%", background: s.color }} />
                  {s.name}
                </span>
                <span
                  style={{
                    flex: 1,
                    minWidth: 0,
                    fontSize: 14,
                    fontWeight: 600,
                    color: T.text,
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                  title={g.name}
                >
                  {g.name}
                </span>
                <span style={{ flexShrink: 0, fontFamily: FONT_MONO, fontSize: 11, color: T.faint2 }}>
                  {g.tracks.length} {g.tracks.length === 1 ? "track" : "tracks"}
                </span>
                {g.playlist && (
                  <a href={api.zipUrl(g.playlist)} style={{ ...ghostBtn, height: 28, padding: "0 10px" }}>
                    .zip
                  </a>
                )}
              </div>

              {g.tracks.map(({ job, meta }) => (
                <div
                  key={job.id}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 11,
                    padding: "10px 15px",
                    borderBottom: "1px solid rgba(255,255,255,0.04)",
                  }}
                >
                  <span
                    style={{ flexShrink: 0, width: 7, height: 7, borderRadius: "50%", background: s.color }}
                  />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div
                      style={{
                        fontSize: 13.5,
                        color: T.text3,
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}
                      title={job.title || job.output_path || ""}
                    >
                      {job.title || job.output_path}
                    </div>
                    {job.source === "spotify" && (
                      <div style={{ fontFamily: FONT_MONO, fontSize: 10, color: T.faint3, marginTop: 2 }}>
                        ↳ from YouTube match
                      </div>
                    )}
                  </div>
                  <span
                    style={{
                      flexShrink: 0,
                      fontFamily: FONT_MONO,
                      fontSize: 10.5,
                      color: T.faint3,
                      letterSpacing: "0.03em",
                    }}
                  >
                    {meta}
                  </span>
                  <a
                    href={api.fileUrl(job.output_path!)}
                    style={{
                      flexShrink: 0,
                      display: "inline-flex",
                      alignItems: "center",
                      justifyContent: "center",
                      width: 28,
                      height: 28,
                      borderRadius: 7,
                      border: `1px solid ${T.borderStrong}`,
                      color: T.muted,
                      textDecoration: "none",
                      fontSize: 13,
                    }}
                  >
                    ↓
                  </a>
                </div>
              ))}
            </div>
          );
        })}
      </div>
    </section>
  );
}

const ghostBtn: React.CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  gap: 7,
  height: 32,
  padding: "0 13px",
  border: `1px solid ${T.borderStrong}`,
  borderRadius: 8,
  background: "rgba(255,255,255,0.04)",
  color: T.text2,
  fontSize: 12,
  textDecoration: "none",
  cursor: "pointer",
};
