import type { AuthProviders, AuthResponse, Job, Organization, SystemInfo, User } from "./types";

const API_BASE = "/api/v1";
const TOKEN_KEY = "stemsplit.accessToken";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export function getStoredToken(): string {
  return localStorage.getItem(TOKEN_KEY) || "";
}

export function storeToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearStoredToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (response.ok) {
    if (response.status === 204) {
      return undefined as T;
    }
    return (await response.json()) as T;
  }
  let message = response.statusText || "Request failed";
  try {
    const payload = (await response.json()) as { detail?: string };
    if (payload.detail) {
      message = payload.detail;
    }
  } catch {
    // Keep the HTTP status text if the response is not JSON.
  }
  throw new ApiError(response.status, message);
}

async function request<T>(path: string, token: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  if (init.body && !(init.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers
  });
  return parseResponse<T>(response);
}

export const api = {
  async register(email: string, password: string, fullName: string, organizationName: string): Promise<AuthResponse> {
    return request<AuthResponse>("/auth/register", "", {
      method: "POST",
      body: JSON.stringify({
        email,
        password,
        full_name: fullName,
        organization_name: organizationName
      })
    });
  },

  async login(email: string, password: string): Promise<AuthResponse> {
    return request<AuthResponse>("/auth/login", "", {
      method: "POST",
      body: JSON.stringify({ email, password })
    });
  },

  async logout(token: string): Promise<void> {
    await request<{ ok: boolean }>("/auth/logout", token, { method: "POST" });
  },

  async providers(): Promise<AuthProviders> {
    return request<AuthProviders>("/auth/providers", "");
  },

  oauthStartUrl(provider: "google" | "apple", mode: "login" | "register"): string {
    return `${API_BASE}/auth/oauth/${provider}/start?mode=${encodeURIComponent(mode)}`;
  },

  async me(token: string): Promise<{ user: User; organization: Organization }> {
    return request<{ user: User; organization: Organization }>("/me", token);
  },

  async system(): Promise<SystemInfo> {
    return request<SystemInfo>("/system", "");
  },

  async listJobs(token: string): Promise<Job[]> {
    return request<Job[]>("/jobs", token);
  },

  async getJob(token: string, jobId: string): Promise<Job> {
    return request<Job>(`/jobs/${encodeURIComponent(jobId)}`, token);
  },

  async cancelJob(token: string, jobId: string): Promise<Job> {
    return request<Job>(`/jobs/${encodeURIComponent(jobId)}/cancel`, token, { method: "POST" });
  },

  async createJob(token: string, file: File, settings: { model: string; segment: number; overlap: number; shifts: number }): Promise<{ job_id: string }> {
    const data = new FormData();
    data.append("file", file);
    data.append("model", settings.model);
    data.append("segment", String(settings.segment));
    data.append("overlap", String(settings.overlap));
    data.append("shifts", String(settings.shifts));
    return request<{ job_id: string }>("/jobs", token, {
      method: "POST",
      body: data
    });
  },

  async fetchStemBlob(token: string, jobId: string, stemName: string): Promise<Blob> {
    const response = await fetch(`${API_BASE}/jobs/${encodeURIComponent(jobId)}/download/${encodeURIComponent(stemName)}`, {
      headers: {
        Authorization: `Bearer ${token}`
      }
    });
    if (!response.ok) {
      throw new ApiError(response.status, response.statusText || "Could not download stem");
    }
    return response.blob();
  }
};
