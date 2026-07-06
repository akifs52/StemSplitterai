export type ViewName = "dashboard" | "mixer" | "settings";

export interface User {
  id: string;
  email: string;
  full_name: string;
  created_at: string;
}

export interface Plan {
  id: string;
  name: string;
  monthly_job_limit: number;
  max_upload_mb: number;
}

export interface Organization {
  id: string;
  name: string;
  slug: string;
  plan?: Plan | null;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
  organization: Organization;
}

export interface AuthProviders {
  google: boolean;
  apple: boolean;
}

export interface JobArtifact {
  id: string;
  name: string;
  content_type: string;
  size_bytes: number;
  created_at: string;
}

export interface Stem {
  name: string;
  path: string;
}

export interface Job {
  id: string;
  source_filename: string;
  source_size_bytes: number;
  model: string;
  segment: number;
  overlap: number;
  shifts: number;
  status: "queued" | "running" | "done" | "error" | "cancelled" | string;
  stage: string;
  progress: number;
  cancel_requested: boolean;
  error_message: string;
  created_at: string;
  started_at?: string | null;
  completed_at?: string | null;
  artifacts: JobArtifact[];
  stems: Stem[];
  waveform: number[];
  stem_waveforms: Record<string, number[]>;
}

export interface SystemInfo {
  gpu: boolean;
  device: string;
  queue_backend: string;
  queue_ready: boolean;
  api_version: string;
}

export type InstallPromptEvent = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed"; platform: string }>;
};
