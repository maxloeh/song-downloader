import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api, openProgressSocket } from "./api";
import AuthScreen from "./components/AuthScreen";
import CompletedSection from "./components/CompletedSection";
import JobRow from "./components/JobRow";
import SoundCloudConnect from "./components/SoundCloudConnect";
import SpotifyConnect from "./components/SpotifyConnect";
import UrlForm from "./components/UrlForm";
import { FONT_MONO, T } from "./theme";
import type { AppConfig, AuthState, DownloadOptions, Job } from "./types";

export default function App() {
  const [auth, setAuth] = useState<AuthState | null>(null);
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [spotifyConfigured, setSpotifyConfigured] = useState(false);
  const [jobs, setJobs] = useState<Record<string, Job>>({});
  const [error, setError] = useState<string | null>(null);
  const [connected, setConnected] = useState(false);
  const [filesRefresh, setFilesRefresh] = useState(0);
  const socketRef = useRef<WebSocket | null>(null);
  const authed = !!auth?.authenticated;

  const upsertJob = useCallback((job: Job) => {
    setJobs((prev) => ({ ...prev, [job.id]: job }));
    if (job.status === "done") setFilesRefresh((k) => k + 1);
  }, []);

  // Determine auth state first; everything else loads only once authenticated.
  useEffect(() => {
    api.getAuthState().then(setAuth).catch(() => setAuth({ needs_setup: false, authenticated: false, username: null }));
  }, []);

  useEffect(() => {
    if (!authed) return;
    api
      .getConfig()
      .then((c) => {
        setConfig(c);
        setSpotifyConfigured(c.spotify_configured);
      })
      .catch((e) => setError(String(e)));
    api.getJobs().then((list) => {
      const map: Record<string, Job> = {};
      list.forEach((j) => (map[j.id] = j));
      setJobs(map);
    });
  }, [authed]);

  // Live progress WebSocket with auto-reconnect.
  useEffect(() => {
    if (!authed) return;
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
        } else if (data.type === "remove") {
          setJobs((prev) => {
            const next = { ...prev };
            delete next[data.id as string];
            return next;
          });
        }
      };
    }
    connect();
    return () => {
      closed = true;
      clearTimeout(retry);
      socketRef.current?.close();
    };
  }, [authed, upsertJob]);

  const handleAuthed = useCallback(() => {
    api.getAuthState().then(setAuth).catch(() => {});
  }, []);

  const handleLogout = useCallback(() => {
    api.logout().finally(() => {
      socketRef.current?.close();
      setJobs({});
      setConfig(null);
      setAuth({ needs_setup: false, authenticated: false, username: null });
    });
  }, []);

  const handleSubmit = useCallback(
    async (urls: string[], options: DownloadOptions) => {
      try {
        await api.submit(urls, options);
        setError(null);
        // Jobs stream in over the WebSocket; also pull once as a fallback.
        setTimeout(() => api.getJobs().then((list) => list.forEach(upsertJob)).catch(() => {}), 500);
      } catch (e) {
        setError(String(e));
      }
    },
    [upsertJob],
  );

  const handleRetry = useCallback(
    // Retry implies "try harder" — ensure the YouTube fallback is on so
    // download-disabled / protected tracks can still resolve.
    (job: Job) => handleSubmit([job.url], { ...job.options, youtube_fallback: true }),
    [handleSubmit],
  );

  const handleDismiss = useCallback((job: Job) => {
    setJobs((prev) => {
      const next = { ...prev };
      delete next[job.id];
      return next;
    });
    api.deleteJob(job.id).catch(() => {});
  }, []);

  const handleClearFailed = useCallback(() => {
    setJobs((prev) =>
      Object.fromEntries(Object.entries(prev).filter(([, j]) => j.status !== "failed")),
    );
    api.clearFailed().catch(() => {});
  }, []);

  const sortedJobs = useMemo(
    () => Object.values(jobs).sort((a, b) => b.created_at - a.created_at),
    [jobs],
  );

  // Hide a failed job when a newer job for the same URL has since succeeded.
  const doneUrls = useMemo(
    () => new Set(sortedJobs.filter((j) => j.status === "done").map((j) => j.url)),
    [sortedJobs],
  );
  const queueJobs = sortedJobs.filter(
    (j) => j.status !== "done" && !(j.status === "failed" && doneUrls.has(j.url)),
  );
  const failedCount = queueJobs.filter((j) => j.status === "failed").length;

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

  // ── Auth gate ──────────────────────────────────────────────────────────────
  if (auth === null) {
    return null; // brief: deciding setup vs login vs app
  }
  if (auth.needs_setup) {
    return <AuthScreen mode="setup" onAuthed={handleAuthed} />;
  }
  if (!auth.authenticated) {
    return <AuthScreen mode="login" onAuthed={handleAuthed} />;
  }

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
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
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
            <button
              type="button"
              onClick={handleLogout}
              title={auth.username ? `Signed in as ${auth.username}` : "Log out"}
              style={{
                fontFamily: FONT_MONO,
                fontSize: 11,
                color: T.faint2,
                background: "rgba(255,255,255,0.04)",
                border: `1px solid ${T.borderStrong}`,
                borderRadius: 999,
                padding: "5px 11px",
                cursor: "pointer",
              }}
            >
              log out
            </button>
          </div>
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
            <UrlForm
              config={config}
              spotifyConfigured={spotifyConfigured}
              onSubmit={handleSubmit}
            />

            <SoundCloudConnect />
            <SpotifyConnect onChange={setSpotifyConfigured} />

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
                  <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                    <span style={{ fontFamily: FONT_MONO, fontSize: 11, color: T.faint2 }}>
                      {countsText}
                    </span>
                    {failedCount > 0 && (
                      <button
                        type="button"
                        onClick={handleClearFailed}
                        style={{
                          fontFamily: FONT_MONO,
                          fontSize: 11,
                          color: "#ff5d73",
                          background: "rgba(255,93,115,0.08)",
                          border: "1px solid rgba(255,93,115,0.25)",
                          borderRadius: 7,
                          padding: "3px 9px",
                          cursor: "pointer",
                        }}
                      >
                        Clear failed
                      </button>
                    )}
                  </div>
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 9 }}>
                  {queueJobs.map((job) => (
                    <JobRow key={job.id} job={job} onRetry={handleRetry} onDismiss={handleDismiss} />
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
