import type {
  AppConfig,
  DownloadOptions,
  FileItem,
  Job,
  SoundcloudStatus,
  SpotifyStatus,
} from "./types";

// Browser-handled Basic Auth: once the initial 401 prompt is satisfied, the
// browser attaches the Authorization header to every subsequent same-origin
// request automatically, so we don't manage credentials in JS.

async function jsonFetch<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  getConfig: () => jsonFetch<AppConfig>("/api/config"),

  getJobs: () => jsonFetch<Job[]>("/api/jobs"),

  deleteJob: (id: string) =>
    jsonFetch<{ removed: number }>(`/api/jobs/${id}`, { method: "DELETE" }),

  clearFailed: () => jsonFetch<{ removed: number }>("/api/jobs", { method: "DELETE" }),

  submit: (urls: string[], options: DownloadOptions) =>
    jsonFetch<{ jobs: Job[] }>("/api/download", {
      method: "POST",
      body: JSON.stringify({ urls, options }),
    }),

  getWsTicket: () => jsonFetch<{ ticket: string }>("/api/ws-ticket"),

  getSoundcloudStatus: () => jsonFetch<SoundcloudStatus>("/api/settings/soundcloud"),

  connectSoundcloud: (token: string) =>
    jsonFetch<SoundcloudStatus>("/api/settings/soundcloud", {
      method: "POST",
      body: JSON.stringify({ token }),
    }),

  disconnectSoundcloud: () =>
    jsonFetch<SoundcloudStatus>("/api/settings/soundcloud", { method: "DELETE" }),

  getSpotifyStatus: () => jsonFetch<SpotifyStatus>("/api/settings/spotify"),

  connectSpotify: (client_id: string, client_secret: string) =>
    jsonFetch<SpotifyStatus>("/api/settings/spotify", {
      method: "POST",
      body: JSON.stringify({ client_id, client_secret }),
    }),

  disconnectSpotify: () =>
    jsonFetch<SpotifyStatus>("/api/settings/spotify", { method: "DELETE" }),

  listFiles: () => jsonFetch<FileItem[]>("/api/files"),

  fileUrl: (path: string) =>
    `/api/files/download?path=${encodeURIComponent(path)}`,

  zipUrl: (path?: string) =>
    `/api/files/zip${path ? `?path=${encodeURIComponent(path)}` : ""}`,
};

/**
 * Open the progress WebSocket. Browsers can't send Basic Auth on a WS
 * handshake, so we first fetch a short-lived ticket over authenticated HTTP and
 * pass it as a query param. Returns the socket; caller wires handlers.
 */
export async function openProgressSocket(): Promise<WebSocket> {
  const { ticket } = await api.getWsTicket();
  const proto = location.protocol === "https:" ? "wss" : "ws";
  return new WebSocket(
    `${proto}://${location.host}/api/ws?ticket=${encodeURIComponent(ticket)}`,
  );
}
