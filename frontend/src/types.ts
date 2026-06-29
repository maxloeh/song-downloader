export type JobStatus =
  | "queued"
  | "downloading"
  | "converting"
  | "done"
  | "failed";

export type Source = "soundcloud" | "spotify";

export interface DownloadOptions {
  format: string;
  bitrate: string;
  soundcloud_original: boolean;
}

export interface Job {
  id: string;
  source: Source;
  url: string;
  title: string | null;
  playlist: string | null;
  options: DownloadOptions;
  status: JobStatus;
  progress: number;
  audio_source: string | null;
  output_path: string | null;
  error: string | null;
  created_at: number;
  updated_at: number;
}

export interface AppConfig {
  formats: string[];
  bitrates: string[];
  default_format: string;
  default_bitrate: string;
  spotify_configured: boolean;
  max_concurrent_downloads: number;
}

export interface FileItem {
  path: string;
  name: string;
  size: number;
  modified: number;
}
