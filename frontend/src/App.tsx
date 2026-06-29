import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api, openProgressSocket } from "./api";
import CompletedSection from "./components/CompletedSection";
import JobRow from "./components/JobRow";
import UrlForm from "./components/UrlForm";
import { FONT_MONO, T } from "./theme";
import type { AppConfig, DownloadOptions, Job } from "./types";

export default function App() {
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [jobs, setJobs] = useState<Record<string, Job>>({});
  const [error, setError] = useState<string | null>(null);
  const [connected, setConnected] = useState(false);
  const [filesRefresh, setFilesRefresh] = useState(0);
  const socketRef = useRef<WebSocket | null>(null);

  const upsertJob = useCallback((job: Job) => {
    setJobs((prev) => ({ ...prev, [job.id]: job }));
    if (job.status === "done") setFilesRefresh((k) => k + 1);
  }, []);

  useEffect(() => {
    api.getConfig().then(setConfig).catch((e) => setError(String(e)));
    api.getJobs().then((list) => {
      const map: Record<string, Job> = {};
      list.forEach((j) => (map[j.id] = j));
      setJobs(map);
    });
  }, []);

  // Live progress WebSocket with auto-reconnect.
  useEffect(() => {
    let closed = false;
    let retry: ReturnType<typeof setTimeout>;

    async function connect() {
      let ws: WebSocket;
      try {
        ws = await openProgressSocket();
      } catch {
        if (!closed) retry = setTimeout(connect, 2000);
        return;
      }
      if (closed) {
        ws.close();
        return;
      }
      socketRef.current = ws;
      ws.onopen = () => setConnected(true);
      ws.onclose = () => {
        setConnected(false);
        if (!closed) retry = setTimeout(connect, 2000);
      };
      ws.onmessage = (ev) => {
        const data = JSON.parse(ev.data);
        if (data.type === "snapshot") {
          const map: Record<string, Job> = {};
          (data.jobs as Job[]).forEach((j) => (map[j.id] = j));
          setJobs(map);
        } else if (data.type === "job") {
          upsertJob(data.job as Job);
        }
      };
    }
    connect();
    return () => {
      closed = true;
      clearTimeout(retry);
      socketRef.current?.close();
    };
  }, [upsertJob]);

  const handleSubmit = useCallback(
    async (urls: string[], options: DownloadOptions) => {
      try {
        const res = await api.submit(urls, options);
        res.jobs.forEach(upsertJob);
        setError(null);
      } catch (e) {
        setError(String(e));
      }
    },
    [upsertJob],
  );

  const handleRetry = useCallback(
    (job: Job) => handleSubmit([job.url], job.options),
    [handleSubmit],
  );

  const sortedJobs = useMemo(
    () => Object.values(jobs).sort((a, b) => b.created_at - a.created_at),
    [jobs],
  );
  const queueJobs = sortedJobs.filter((j) => j.status !== "done");

  const counts = useMemo(() => {
    const c = { queued: 0, active: 0, done: 0, failed: 0 };
    sortedJobs.forEach((j) => {
      if (j.status === "done") c.done++;
      else if (j.status === "failed") c.failed++;
      else if (j.status === "queued") c.queued++;
      else c.active++;
    });
    return c;
  }, [sortedJobs]);

  const countsText = `${counts.queued} queued · ${counts.active} active · ${counts.done} done · ${counts.failed} failed`;

  return (
    <div style={{ position: "relative", zIndex: 1, padding: "30px 14px 90px" }}>
      <div style={{ maxWidth: 880, margin: "0 auto" }}>
        {/* Header */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 16,
            marginBottom: 22,
            flexWrap: "wrap",
          }}
        >
          <div>
            <h2 style={{ margin: 0, fontSize: 23, fontWeight: 600, letterSpacing: "-0.02em" }}>
              Drop your links
            </h2>
            <p style={{ margin: "5px 0 0", fontSize: 13, color: T.muted }}>
              Paste one or more URLs — one per line. We detect the source automatically.
            </p>
          </div>
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 7,
              fontFamily: FONT_MONO,
              fontSize: 11,
              color: connected ? "#2fe0a6" : T.faint2,
              background: connected ? "rgba(47,224,166,0.12)" : "rgba(146,152,166,0.1)",
              border: `1px solid ${connected ? "rgba(47,224,166,0.2)" : "rgba(146,152,166,0.18)"}`,
              borderRadius: 999,
              padding: "5px 11px",
            }}
            title={connected ? "Live updates connected" : "Reconnecting…"}
          >
            <span
              style={{
                width: 6,
                height: 6,
                borderRadius: "50%",
                background: connected ? "#2fe0a6" : T.faint2,
                boxShadow: connected ? "0 0 8px #2fe0a6" : "none",
              }}
            />
            {connected ? "live" : "offline"}
          </span>
        </div>

        {error && (
          <div
            style={{
              marginBottom: 16,
              borderRadius: 9,
              border: "1px solid rgba(255,93,115,0.2)",
              background: "rgba(255,93,115,0.08)",
              padding: "10px 13px",
              fontSize: 13,
              color: "#e3a3ac",
            }}
          >
            {error}
          </div>
        )}

        {config ? (
          <>
            <UrlForm config={config} onSubmit={handleSubmit} />

            {queueJobs.length > 0 && (
              <div style={{ marginTop: 26 }}>
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
                    Queue
                  </h3>
                  <span style={{ fontFamily: FONT_MONO, fontSize: 11, color: T.faint2 }}>
                    {countsText}
                  </span>
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 9 }}>
                  {queueJobs.map((job) => (
                    <JobRow key={job.id} job={job} onRetry={handleRetry} />
                  ))}
                </div>
              </div>
            )}

            <CompletedSection jobs={sortedJobs} refreshKey={filesRefresh} />
          </>
        ) : (
          !error && <p style={{ fontSize: 13, color: T.faint2 }}>Loading…</p>
        )}

        <footer
          style={{
            marginTop: 48,
            textAlign: "center",
            fontFamily: FONT_MONO,
            fontSize: 10,
            color: T.faint4,
            letterSpacing: "0.04em",
          }}
        >
          private instance · for content you're entitled to download
        </footer>
      </div>
    </div>
  );
}
