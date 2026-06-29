import { api } from "../api";
import type { Job } from "../types";

const STATUS_STYLES: Record<Job["status"], string> = {
  queued: "bg-slate-500/15 text-slate-300",
  downloading: "bg-sky-500/15 text-sky-300",
  converting: "bg-violet-500/15 text-violet-300",
  done: "bg-emerald-500/15 text-emerald-300",
  failed: "bg-rose-500/15 text-rose-300",
};

function SourceBadge({ source }: { source: Job["source"] }) {
  const isSpotify = source === "spotify";
  return (
    <span
      className={`badge ${isSpotify ? "bg-spotify/15 text-spotify" : "bg-soundcloud/15 text-soundcloud"}`}
    >
      {isSpotify ? "Spotify" : "SoundCloud"}
    </span>
  );
}

export default function JobRow({ job }: { job: Job }) {
  const active = job.status === "downloading" || job.status === "converting";
  const title = job.title || job.url;

  return (
    <div className="flex flex-col gap-2 rounded-xl border border-white/5 bg-ink-800/50 p-3.5">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <SourceBadge source={job.source} />
            <span className={`badge ${STATUS_STYLES[job.status]}`}>{job.status}</span>
          </div>
          <p className="mt-1.5 truncate text-sm font-medium text-slate-100" title={title}>
            {title}
          </p>
          {job.playlist && (
            <p className="truncate text-xs text-slate-400">in “{job.playlist}”</p>
          )}
        </div>

        {job.status === "done" && job.output_path && (
          <a href={api.fileUrl(job.output_path)} className="btn-ghost shrink-0 px-3 py-1.5 text-xs">
            ↓ Save
          </a>
        )}
      </div>

      {active && (
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/5">
          <div
            className={`h-full rounded-full bg-accent transition-all duration-300 ${
              job.status === "converting" ? "shimmer" : ""
            }`}
            style={{ width: `${Math.max(4, job.progress)}%` }}
          />
        </div>
      )}

      {job.source === "spotify" && job.status === "done" && (
        <p className="text-[11px] text-slate-500">
          Audio matched from YouTube{job.audio_source ? ` (${job.audio_source})` : ""} — bitrate
          is capped by that source.
        </p>
      )}

      {job.status === "failed" && job.error && (
        <p className="rounded-lg bg-rose-500/10 px-2.5 py-1.5 text-xs text-rose-300">
          {job.error}
        </p>
      )}
    </div>
  );
}
