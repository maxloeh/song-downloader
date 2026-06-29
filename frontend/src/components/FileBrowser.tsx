import { useEffect, useState } from "react";
import { api } from "../api";
import type { FileItem } from "../types";

function formatSize(bytes: number): string {
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

export default function FileBrowser({ refreshKey }: { refreshKey: number }) {
  const [files, setFiles] = useState<FileItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    api
      .listFiles()
      .then((f) => !cancelled && setFiles(f))
      .catch(() => {})
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [refreshKey]);

  return (
    <section className="card p-5 sm:p-6">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-400">
          Completed files
        </h2>
        {files.length > 0 && (
          <a href={api.zipUrl()} className="btn-ghost px-3 py-1.5 text-xs">
            ⬇ Download all (zip)
          </a>
        )}
      </div>

      {loading ? (
        <p className="text-sm text-slate-500">Loading…</p>
      ) : files.length === 0 ? (
        <p className="text-sm text-slate-500">No files yet. Downloads will appear here.</p>
      ) : (
        <ul className="divide-y divide-white/5">
          {files.map((f) => (
            <li key={f.path} className="flex items-center justify-between gap-3 py-2.5">
              <div className="min-w-0">
                <p className="truncate text-sm text-slate-100" title={f.path}>
                  {f.name}
                </p>
                <p className="truncate text-xs text-slate-500">{f.path}</p>
              </div>
              <div className="flex shrink-0 items-center gap-3">
                <span className="text-xs text-slate-500">{formatSize(f.size)}</span>
                <a href={api.fileUrl(f.path)} className="btn-ghost px-3 py-1.5 text-xs">
                  ↓
                </a>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
