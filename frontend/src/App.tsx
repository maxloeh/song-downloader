import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api, openProgressSocket } from "./api";
import FileBrowser from "./components/FileBrowser";
import JobRow from "./components/JobRow";
import UrlForm from "./components/UrlForm";
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

  // Bootstrap config + initial jobs.
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

    function connect() {
      const ws = openProgressSocket();
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

  const sortedJobs = useMemo(
    () => Object.values(jobs).sort((a, b) => b.created_at - a.created_at),
    [jobs],
  );
  const active = sortedJobs.filter((j) => j.status !== "done");
  const counts = useMemo(() => {
    const c = { queued: 0, downloading: 0, done: 0, failed: 0 };
    sortedJobs.forEach((j) => {
      if (j.status === "done") c.done++;
      else if (j.status === "failed") c.failed++;
      else if (j.status === "queued") c.queued++;
      else c.downloading++;
    });
    return c;
  }, [sortedJobs]);

  return (
    <div className="mx-auto min-h-full max-w-3xl px-4 py-8 sm:py-12">
      <header className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight text-white">
            <span className="text-accent">♪</span> Music Downloader
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            SoundCloud &amp; Spotify → tagged files with cover art.
          </p>
        </div>
        <span
          className={`badge ${connected ? "bg-emerald-500/15 text-emerald-300" : "bg-slate-500/15 text-slate-400"}`}
          title={connected ? "Live updates connected" : "Reconnecting…"}
        >
          <span
            className={`h-1.5 w-1.5 rounded-full ${connected ? "bg-emerald-400" : "bg-slate-500"}`}
          />
          {connected ? "live" : "offline"}
        </span>
      </header>

      {error && (
        <div className="mb-4 rounded-xl border border-rose-500/20 bg-rose-500/10 px-4 py-3 text-sm text-rose-300">
          {error}
        </div>
      )}

      {config ? (
        <div className="space-y-6">
          <UrlForm config={config} onSubmit={handleSubmit} />

          <section className="card p-5 sm:p-6">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-400">
                Queue
              </h2>
              <p className="text-xs text-slate-500">
                {counts.queued} queued · {counts.downloading} active · {counts.done} done ·{" "}
                {counts.failed} failed
              </p>
            </div>
            {active.length === 0 ? (
              <p className="text-sm text-slate-500">
                Nothing in progress. Paste a link above to start.
              </p>
            ) : (
              <div className="space-y-2.5">
                {active.map((job) => (
                  <JobRow key={job.id} job={job} />
                ))}
              </div>
            )}
          </section>

          <FileBrowser refreshKey={filesRefresh} />
        </div>
      ) : (
        !error && <p className="text-sm text-slate-500">Loading…</p>
      )}

      <footer className="mt-12 text-center text-xs text-slate-600">
        Private self-hosted instance · for content you're entitled to download.
      </footer>
    </div>
  );
}
