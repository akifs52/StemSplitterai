import {
  CheckCircle2,
  CircleAlert,
  Cpu,
  Download,
  HardDriveDownload,
  History,
  Loader2,
  LogOut,
  Music2,
  Pause,
  Play,
  Settings,
  SlidersHorizontal,
  UploadCloud,
  UserRound,
  WifiOff,
  X
} from "lucide-react";
import { FormEvent, PointerEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";

import { ApiError, api, clearStoredToken, getStoredToken, storeToken } from "./api";
import type { AuthProviders, InstallPromptEvent, Job, Organization, SystemInfo, User, ViewName } from "./types";
import { drawWave } from "./waveform";

const palette = ["#ff4d6d", "#4fc3f7", "#ffd166", "#8be9c1", "#c77dff", "#ff9f1c", "#2ec4b6", "#e76f51"];
const terminalStatuses = new Set(["done", "error", "cancelled"]);

type AuthMode = "login" | "register";

function GoogleIcon() {
  return (
    <svg aria-hidden="true" focusable="false" viewBox="0 0 24 24">
      <path
        fill="#4285F4"
        d="M23.49 12.27c0-.79-.07-1.54-.2-2.27H12v4.29h6.47c-.28 1.5-1.13 2.77-2.4 3.62v3.01h3.89c2.27-2.09 3.53-5.17 3.53-8.65z"
      />
      <path
        fill="#34A853"
        d="M12 24c3.24 0 5.96-1.07 7.95-2.91l-3.89-3.01c-1.08.72-2.45 1.15-4.06 1.15-3.12 0-5.77-2.11-6.72-4.95H1.26v3.1C3.24 21.3 7.3 24 12 24z"
      />
      <path
        fill="#FBBC05"
        d="M5.28 14.28c-.24-.72-.38-1.48-.38-2.28s.14-1.56.38-2.28v-3.1H1.26C.45 8.24 0 10.06 0 12s.45 3.76 1.26 5.38l4.02-3.1z"
      />
      <path
        fill="#EA4335"
        d="M12 4.77c1.76 0 3.34.61 4.59 1.8l3.44-3.44C17.95 1.19 15.23 0 12 0 7.3 0 3.24 2.7 1.26 6.62l4.02 3.1C6.23 6.88 8.88 4.77 12 4.77z"
      />
    </svg>
  );
}

function AppleIcon() {
  return (
    <svg aria-hidden="true" focusable="false" viewBox="0 0 24 24">
      <path
        fill="currentColor"
        d="M16.7 13.2c0-2.5 2.1-3.7 2.2-3.8-1.2-1.7-3-1.9-3.6-2-1.5-.2-3 .9-3.8.9-.8 0-2-.9-3.3-.9-1.7 0-3.3 1-4.2 2.6-1.8 3.1-.5 7.7 1.3 10.2.9 1.2 1.9 2.6 3.2 2.5 1.3-.1 1.8-.8 3.4-.8 1.6 0 2 .8 3.4.8 1.4 0 2.3-1.2 3.2-2.5 1-1.4 1.4-2.8 1.4-2.9-.1 0-2.7-1-2.7-4.1zM14.3 5.8c.7-.9 1.2-2.1 1.1-3.3-1.1 0-2.4.7-3.1 1.6-.7.8-1.3 2-1.1 3.2 1.2.1 2.4-.6 3.1-1.5z"
      />
    </svg>
  );
}

function consumeOAuthHash(): { token: string; error: string } {
  if (!window.location.hash) {
    return { token: "", error: "" };
  }
  const params = new URLSearchParams(window.location.hash.slice(1));
  const token = params.get("access_token") || "";
  const error = params.get("oauth_error") || "";
  if (token) {
    storeToken(token);
  }
  if (token || error) {
    window.history.replaceState(null, "", "/");
  }
  return { token, error };
}

const initialOAuth = consumeOAuthHash();

function formatBytes(bytes: number): string {
  if (!bytes) {
    return "0 B";
  }
  const units = ["B", "KB", "MB", "GB"];
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return `${(bytes / 1024 ** index).toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

function formatTime(seconds: number): string {
  const safe = Number.isFinite(seconds) ? Math.max(0, Math.floor(seconds)) : 0;
  const mins = Math.floor(safe / 60);
  const secs = safe % 60;
  return `${mins}:${String(secs).padStart(2, "0")}`;
}

function popupText(text: string): string {
  const match = (text || "").match(/Initializing Demucs \(([^)]+)\)/);
  return match ? match[1] : text || "Processing...";
}

function statusLabel(job?: Job | null): string {
  if (!job) {
    return "No active job";
  }
  if (job.status === "done") {
    return "Complete";
  }
  if (job.status === "error") {
    return "Failed";
  }
  if (job.status === "cancelled") {
    return "Cancelled";
  }
  return popupText(job.stage);
}

function WaveCanvas({
  data,
  color,
  position = 0,
  mode = "center",
  showProgress = true,
  className = "",
  height = 150
}: {
  data: number[];
  color: string;
  position?: number;
  mode?: "center" | "bottom";
  showProgress?: boolean;
  className?: string;
  height?: number;
}) {
  const ref = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) {
      return;
    }
    const render = () => drawWave(canvas, data, color, position, mode, showProgress);
    render();
    const observer = new ResizeObserver(render);
    observer.observe(canvas);
    return () => observer.disconnect();
  }, [color, data, height, mode, position, showProgress]);

  return <canvas ref={ref} className={className} height={height} />;
}

export function App() {
  const [token, setToken] = useState(initialOAuth.token || getStoredToken());
  const [user, setUser] = useState<User | null>(null);
  const [organization, setOrganization] = useState<Organization | null>(null);
  const [system, setSystem] = useState<SystemInfo | null>(null);
  const [authProviders, setAuthProviders] = useState<AuthProviders>({ google: false, apple: false });
  const [bootstrapping, setBootstrapping] = useState(Boolean(initialOAuth.token || getStoredToken()));

  const [authMode, setAuthMode] = useState<AuthMode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [organizationName, setOrganizationName] = useState("");
  const [authError, setAuthError] = useState(initialOAuth.error);
  const [authBusy, setAuthBusy] = useState(false);

  const [view, setView] = useState<ViewName>("dashboard");
  const [jobs, setJobs] = useState<Job[]>([]);
  const [currentJob, setCurrentJob] = useState<Job | null>(null);
  const [uploadError, setUploadError] = useState("");
  const [uploading, setUploading] = useState(false);
  const [model, setModel] = useState("htdemucs_6s");
  const [segment, setSegment] = useState(5);
  const [overlap, setOverlap] = useState(0.25);
  const [shifts, setShifts] = useState(1);

  const [stemUrls, setStemUrls] = useState<Record<string, string>>({});
  const [stemUrlError, setStemUrlError] = useState("");
  const [colors, setColors] = useState<Record<string, string>>({});
  const [stemVolumes, setStemVolumes] = useState<Record<string, number>>({});
  const [muted, setMuted] = useState<Record<string, boolean>>({});
  const [solo, setSolo] = useState("");
  const [masterVolume, setMasterVolume] = useState(0.8);
  const [playing, setPlaying] = useState(false);
  const [position, setPosition] = useState(0);
  const [duration, setDuration] = useState(0);

  const [installPrompt, setInstallPrompt] = useState<InstallPromptEvent | null>(null);
  const [online, setOnline] = useState(navigator.onLine);

  const audioRefs = useRef<Record<string, HTMLAudioElement | null>>({});

  const currentStems = currentJob?.stems || [];
  const playbackRatio = duration > 0 ? Math.max(0, Math.min(1, position / duration)) : 0;
  const activeJobRunning = Boolean(currentJob && !terminalStatuses.has(currentJob.status));

  const upsertJob = useCallback((job: Job) => {
    setJobs((items) =>
      [job, ...items.filter((item) => item.id !== job.id)].sort(
        (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      )
    );
  }, []);

  const handleUnauthorized = useCallback((error: unknown) => {
    if (error instanceof ApiError && error.status === 401) {
      clearStoredToken();
      setToken("");
      setUser(null);
      setOrganization(null);
      setJobs([]);
      setCurrentJob(null);
      return true;
    }
    return false;
  }, []);

  const loadJob = useCallback(
    async (jobId: string, switchToMixer = false, authToken = token) => {
      if (!authToken) {
        return;
      }
      try {
        const fresh = await api.getJob(authToken, jobId);
        setCurrentJob(fresh);
        upsertJob(fresh);
        if (switchToMixer || fresh.status === "done") {
          setView("mixer");
        }
      } catch (error) {
        handleUnauthorized(error);
      }
    },
    [handleUnauthorized, token, upsertJob]
  );

  const refreshJobs = useCallback(
    async (authToken = token) => {
      if (!authToken) {
        return;
      }
      try {
        const rows = await api.listJobs(authToken);
        setJobs(rows);
        setCurrentJob((previous) => previous || rows[0] || null);
      } catch (error) {
        handleUnauthorized(error);
      }
    },
    [handleUnauthorized, token]
  );

  useEffect(() => {
    let cancelled = false;
    async function bootstrap() {
      setBootstrapping(Boolean(token));
      try {
        const [identity, systemInfo, providerInfo] = await Promise.all([
          token ? api.me(token) : null,
          api.system(),
          api.providers()
        ]);
        if (cancelled) {
          return;
        }
        setSystem(systemInfo);
        setAuthProviders(providerInfo);
        if (identity) {
          setUser(identity.user);
          setOrganization(identity.organization);
          await refreshJobs(token);
        }
      } catch (error) {
        if (!handleUnauthorized(error)) {
          setAuthError(error instanceof Error ? error.message : "Could not initialize session");
        }
      } finally {
        if (!cancelled) {
          setBootstrapping(false);
        }
      }
    }
    bootstrap();
    return () => {
      cancelled = true;
    };
  }, [handleUnauthorized, refreshJobs, token]);

  useEffect(() => {
    const updateOnline = () => setOnline(navigator.onLine);
    const handleInstall = (event: Event) => {
      event.preventDefault();
      setInstallPrompt(event as InstallPromptEvent);
    };
    window.addEventListener("online", updateOnline);
    window.addEventListener("offline", updateOnline);
    window.addEventListener("beforeinstallprompt", handleInstall);
    window.addEventListener("appinstalled", () => setInstallPrompt(null));
    return () => {
      window.removeEventListener("online", updateOnline);
      window.removeEventListener("offline", updateOnline);
      window.removeEventListener("beforeinstallprompt", handleInstall);
    };
  }, []);

  useEffect(() => {
    if (!currentJob || terminalStatuses.has(currentJob.status) || !token) {
      return;
    }
    const timer = window.setInterval(async () => {
      try {
        const fresh = await api.getJob(token, currentJob.id);
        setCurrentJob(fresh);
        upsertJob(fresh);
        if (fresh.status === "done") {
          setView("mixer");
        }
      } catch (error) {
        handleUnauthorized(error);
      }
    }, 1000);
    return () => window.clearInterval(timer);
  }, [currentJob, handleUnauthorized, token, upsertJob]);

  useEffect(() => {
    setStemUrls({});
    setStemUrlError("");
    setPlaying(false);
    setMuted({});
    setSolo("");
    setPosition(0);
    setDuration(0);
    const nextColors: Record<string, string> = {};
    currentStems.forEach((stem, index) => {
      nextColors[stem.name] = palette[index % palette.length];
    });
    setColors(nextColors);
    setStemVolumes((previous) => {
      const next: Record<string, number> = {};
      currentStems.forEach((stem) => {
        next[stem.name] = previous[stem.name] ?? 1;
      });
      return next;
    });
  }, [currentJob?.id]);

  useEffect(() => {
    if (!token || currentJob?.status !== "done" || !currentStems.length) {
      return;
    }
    let cancelled = false;
    const jobId = currentJob.id;
    const urls: Record<string, string> = {};
    async function loadStemUrls() {
      setStemUrlError("");
      try {
        await Promise.all(
          currentStems.map(async (stem) => {
            const blob = await api.fetchStemBlob(token, jobId, stem.name);
            urls[stem.name] = URL.createObjectURL(blob);
          })
        );
        if (!cancelled) {
          setStemUrls(urls);
        }
      } catch (error) {
        if (!cancelled) {
          setStemUrlError(error instanceof Error ? error.message : "Could not load stem audio");
        }
      }
    }
    loadStemUrls();
    return () => {
      cancelled = true;
      Object.values(urls).forEach((url) => URL.revokeObjectURL(url));
    };
  }, [currentJob?.id, currentJob?.status, currentStems, token]);

  useEffect(() => {
    Object.entries(audioRefs.current).forEach(([name, player]) => {
      if (!player) {
        return;
      }
      const soloActive = Boolean(solo);
      const audible = soloActive ? solo === name : !muted[name];
      const gain = audible ? stemVolumes[name] ?? 1 : 0;
      player.volume = Math.max(0, Math.min(1, gain * masterVolume));
    });
  }, [masterVolume, muted, solo, stemVolumes, stemUrls]);

  useEffect(() => {
    if (!playing) {
      return;
    }
    let frame = 0;
    const sync = () => {
      const players = Object.values(audioRefs.current).filter(Boolean) as HTMLAudioElement[];
      const primary = players[0];
      if (primary) {
        setPosition(primary.currentTime || 0);
        setDuration(Math.max(...players.map((player) => player.duration || 0), 0));
        players.forEach((player) => {
          if (player !== primary && !player.paused && Number.isFinite(player.duration)) {
            if (Math.abs((player.currentTime || 0) - (primary.currentTime || 0)) > 0.14) {
              player.currentTime = Math.min(primary.currentTime || 0, player.duration || primary.currentTime || 0);
            }
          }
        });
      }
      frame = window.requestAnimationFrame(sync);
    };
    frame = window.requestAnimationFrame(sync);
    return () => window.cancelAnimationFrame(frame);
  }, [playing, stemUrls]);

  const submitAuth = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setAuthBusy(true);
    setAuthError("");
    try {
      const response =
        authMode === "register"
          ? await api.register(email, password, fullName, organizationName)
          : await api.login(email, password);
      storeToken(response.access_token);
      setToken(response.access_token);
      setUser(response.user);
      setOrganization(response.organization);
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : "Authentication failed");
    } finally {
      setAuthBusy(false);
    }
  };

  const startOAuth = (provider: "google" | "apple") => {
    setAuthError("");
    window.location.href = api.oauthStartUrl(provider, authMode);
  };

  const logout = async () => {
    if (token) {
      try {
        await api.logout(token);
      } catch {
        // Local logout still clears the client state.
      }
    }
    clearStoredToken();
    setToken("");
    setUser(null);
    setOrganization(null);
    setJobs([]);
    setCurrentJob(null);
    setView("dashboard");
  };

  const uploadFile = async (file: File) => {
    if (!token) {
      return;
    }
    setUploading(true);
    setUploadError("");
    try {
      const created = await api.createJob(token, file, { model, segment, overlap, shifts });
      const job = await api.getJob(token, created.job_id);
      setCurrentJob(job);
      upsertJob(job);
      setView("dashboard");
    } catch (error) {
      if (!handleUnauthorized(error)) {
        setUploadError(error instanceof Error ? error.message : "Upload failed");
      }
    } finally {
      setUploading(false);
    }
  };

  const cancelCurrentJob = async () => {
    if (!token || !currentJob) {
      return;
    }
    try {
      const job = await api.cancelJob(token, currentJob.id);
      setCurrentJob(job);
      upsertJob(job);
    } catch (error) {
      if (!handleUnauthorized(error)) {
        setUploadError(error instanceof Error ? error.message : "Could not cancel job");
      }
    }
  };

  const togglePlayback = async () => {
    const players = Object.values(audioRefs.current).filter(Boolean) as HTMLAudioElement[];
    if (!players.length) {
      return;
    }
    if (playing) {
      players.forEach((player) => player.pause());
      setPlaying(false);
      return;
    }
    const startAt = Math.min(...players.map((player) => player.currentTime || 0));
    await Promise.all(
      players.map((player) => {
        player.currentTime = startAt;
        return player.play().catch(() => null);
      })
    );
    setPlaying(true);
  };

  const seekAll = (event: PointerEvent<HTMLDivElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const ratio = Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width));
    const target = ratio * duration;
    Object.values(audioRefs.current).forEach((player) => {
      if (player && Number.isFinite(player.duration) && player.duration > 0) {
        player.currentTime = Math.min(target, player.duration);
      }
    });
    setPosition(target);
  };

  const downloadStem = (stemName: string) => {
    const url = stemUrls[stemName];
    if (!url) {
      return;
    }
    const link = document.createElement("a");
    link.href = url;
    link.download = `${stemName}.wav`;
    link.click();
  };

  const installApp = async () => {
    if (!installPrompt) {
      return;
    }
    await installPrompt.prompt();
    await installPrompt.userChoice;
    setInstallPrompt(null);
  };

  const activeStemLabel = useMemo(() => {
    if (!currentStems.length) {
      return "mix";
    }
    if (solo) {
      return solo;
    }
    const active = currentStems.filter((stem) => !muted[stem.name] && (stemVolumes[stem.name] ?? 1) > 0);
    return active.length === 0 ? "muted" : active.length === 1 ? active[0].name : "mix";
  }, [currentStems, muted, solo, stemVolumes]);

  if (bootstrapping) {
    return (
      <main className="boot-screen">
        <section className="splash-card" aria-label="Loading StemSplit AI">
          <div className="splash-mark">
            <img src="/static/pwa-192.png" alt="" />
          </div>
          <div>
            <h1>StemSplit AI</h1>
            <p>Syncing your workspace</p>
          </div>
          <div className="splash-progress" aria-hidden="true">
            <span />
          </div>
        </section>
      </main>
    );
  }

  if (!token || !user || !organization) {
    return (
      <main className="auth-page">
        <section className="auth-panel">
          <div>
            <div className="brand-lockup">
              <Music2 size={26} />
              <span>StemSplit AI</span>
            </div>
            <h1>{authMode === "register" ? "Create your workspace" : "Sign in to your workspace"}</h1>
          </div>
          <form onSubmit={submitAuth} className="auth-form">
            <label>
              <span>Email</span>
              <input autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} type="email" required />
            </label>
            <label>
              <span>Password</span>
              <input
                autoComplete={authMode === "register" ? "new-password" : "current-password"}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                type="password"
                minLength={8}
                required
              />
            </label>
            {authMode === "register" && (
              <>
                <label>
                  <span>Full name</span>
                  <input value={fullName} onChange={(event) => setFullName(event.target.value)} />
                </label>
                <label>
                  <span>Organization</span>
                  <input value={organizationName} onChange={(event) => setOrganizationName(event.target.value)} />
                </label>
              </>
            )}
            {authError && <p className="error-line">{authError}</p>}
            <button className="primary-btn" disabled={authBusy} type="submit">
              {authBusy ? <Loader2 className="spin" size={17} /> : <UserRound size={17} />}
              {authMode === "register" ? "Create account" : "Sign in"}
            </button>
          </form>
          <div className="social-auth-block">
            <div className="auth-divider"><span>or continue with</span></div>
            <div className="provider-grid">
              <button
                className="provider-btn"
                disabled={!authProviders.google || authBusy}
                onClick={() => startOAuth("google")}
                title={authProviders.google ? "Continue with Google" : "Google OAuth is not configured"}
                type="button"
              >
                <span className="provider-mark google-mark">
                  <GoogleIcon />
                </span>
                Continue with Google
              </button>
              <button
                className="provider-btn"
                disabled={!authProviders.apple || authBusy}
                onClick={() => startOAuth("apple")}
                title={authProviders.apple ? "Continue with Apple" : "Apple OAuth is not configured"}
                type="button"
              >
                <span className="provider-mark apple-mark">
                  <AppleIcon />
                </span>
                Continue with Apple
              </button>
            </div>
          </div>
          <button className="text-btn" onClick={() => setAuthMode(authMode === "register" ? "login" : "register")}>
            {authMode === "register" ? "I already have an account" : "Create a new workspace"}
          </button>
          {!online && (
            <div className="offline-note">
              <WifiOff size={16} />
              API access requires a network connection.
            </div>
          )}
        </section>
      </main>
    );
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand-lockup">
          <Music2 size={24} />
          <span>StemSplit AI</span>
        </div>
        <nav className="tabs">
          <button className={view === "dashboard" ? "active" : ""} onClick={() => setView("dashboard")}>
            <UploadCloud size={16} />
            Dashboard
          </button>
          <button className={view === "mixer" ? "active" : ""} onClick={() => setView("mixer")}>
            <SlidersHorizontal size={16} />
            Mixer
          </button>
          <button className={view === "settings" ? "active" : ""} onClick={() => setView("settings")}>
            <Settings size={16} />
            Settings
          </button>
        </nav>
        <div className="top-actions">
          {!online && <WifiOff className="offline-icon" size={18} />}
          {installPrompt && (
            <button className="icon-btn" onClick={installApp} title="Install app">
              <HardDriveDownload size={18} />
            </button>
          )}
          <div className="device-badge">{system?.device || "CPU"}</div>
          <button className="icon-btn" onClick={logout} title="Log out">
            <LogOut size={18} />
          </button>
        </div>
      </header>

      <section className={`view ${view === "dashboard" ? "active" : ""}`}>
        <div className="section-title">
          <h1>Source Separation</h1>
          <p>{organization.name} workspace</p>
        </div>
        <div className="dashboard-grid">
          <label
            className="drop-zone"
            onDragOver={(event) => event.preventDefault()}
            onDrop={(event) => {
              event.preventDefault();
              const file = event.dataTransfer.files[0];
              if (file) {
                uploadFile(file);
              }
            }}
          >
            <input type="file" accept="audio/*" onChange={(event) => event.target.files?.[0] && uploadFile(event.target.files[0])} />
            {uploading ? <Loader2 className="spin upload-icon" size={42} /> : <UploadCloud className="upload-icon" size={42} />}
            <strong>{uploading ? "Uploading..." : "Drop or choose audio"}</strong>
            <small>MP3, WAV, FLAC, M4A, OGG</small>
          </label>

          <aside className="job-panel">
            <div className="panel-head">
              <strong>Current Job</strong>
              <span>{currentJob ? `${currentJob.progress || 0}%` : "idle"}</span>
            </div>
            <div className="status-card">
              <div className={`status-dot ${currentJob?.status || "idle"}`} />
              <div>
                <strong>{statusLabel(currentJob)}</strong>
                <small>{currentJob?.source_filename || "Upload a file to start."}</small>
              </div>
            </div>
            <div className="progress-bar">
              <span style={{ width: `${currentJob?.progress || 0}%` }} />
            </div>
            {activeJobRunning && (
              <button className="danger-btn" onClick={cancelCurrentJob}>
                <X size={16} />
                Cancel job
              </button>
            )}
            {uploadError && <p className="error-line">{uploadError}</p>}
          </aside>
        </div>

        <div className="wave-panel">
          <div className="panel-head">
            <strong>Original Waveform</strong>
            <span>{currentJob?.source_filename || "No source loaded"}</span>
          </div>
          <WaveCanvas data={currentJob?.waveform || []} color="#00e388" position={playbackRatio} className="original-wave" />
        </div>

        <div className="history-panel">
          <div className="panel-head">
            <strong>
              <History size={16} />
              Job History
            </strong>
            <button className="text-btn compact" onClick={() => refreshJobs()}>
              Refresh
            </button>
          </div>
          <div className="job-list">
            {jobs.map((job) => (
              <button
                key={job.id}
                className={`job-row ${currentJob?.id === job.id ? "selected" : ""}`}
                onClick={() => loadJob(job.id, job.status === "done")}
              >
                <span>
                  <strong>{job.source_filename}</strong>
                  <small>{formatBytes(job.source_size_bytes)} · {job.model}</small>
                </span>
                <span className={`job-status ${job.status}`}>{job.status}</span>
              </button>
            ))}
            {!jobs.length && <p className="muted-copy">No jobs yet.</p>}
          </div>
        </div>
      </section>

      <section className={`view mixer-view ${view === "mixer" ? "active" : ""}`}>
        <div className="section-title">
          <h1>Stem Mixer</h1>
          <p>{currentJob?.status === "done" ? "Fine-tune individual components of your track." : "A completed job is required for mixing."}</p>
        </div>
        {stemUrlError && <p className="error-line">{stemUrlError}</p>}
        <div className="stem-list">
          {currentJob?.status === "done" && currentStems.length ? (
            currentStems.map((stem, index) => {
              const color = colors[stem.name] || palette[index % palette.length];
              const src = stemUrls[stem.name] || "";
              return (
                <article className="stem" style={{ color }} key={stem.name}>
                  <div className="stem-info">
                    <div className="stem-label">STEM {String(index + 1).padStart(2, "0")}</div>
                    <div className="stem-name">{stem.name}</div>
                  </div>
                  <div className="stem-wave-wrap">
                    <WaveCanvas
                      data={currentJob.stem_waveforms?.[stem.name] || []}
                      color={color}
                      position={1}
                      mode="bottom"
                      showProgress={false}
                      height={64}
                      className="stem-wave"
                    />
                  </div>
                  <div className="stem-actions">
                    <label className="gain-control">
                      <span>GAIN</span>
                      <input
                        type="range"
                        min="0"
                        max="100"
                        value={(stemVolumes[stem.name] ?? 1) * 100}
                        onChange={(event) =>
                          setStemVolumes((previous) => ({
                            ...previous,
                            [stem.name]: Number(event.target.value) / 100
                          }))
                        }
                      />
                    </label>
                    <div className="stem-buttons">
                      <button
                        className={`mini-btn ${muted[stem.name] ? "active-mute" : ""}`}
                        onClick={() => setMuted((previous) => ({ ...previous, [stem.name]: !previous[stem.name] }))}
                        title="Mute"
                      >
                        M
                      </button>
                      <button className={`mini-btn ${solo === stem.name ? "active-solo" : ""}`} onClick={() => setSolo(solo === stem.name ? "" : stem.name)} title="Solo">
                        S
                      </button>
                      <button className="mini-btn" disabled={!src} onClick={() => downloadStem(stem.name)} title="Download">
                        <Download size={17} />
                      </button>
                    </div>
                  </div>
                  <audio
                    ref={(node) => {
                      audioRefs.current[stem.name] = node;
                    }}
                    src={src}
                    preload="auto"
                    onLoadedMetadata={(event) => setDuration((value) => Math.max(value, event.currentTarget.duration || 0))}
                    onEnded={() => {
                      const players = Object.values(audioRefs.current).filter(Boolean) as HTMLAudioElement[];
                      if (players.every((player) => player.paused || player.ended)) {
                        setPlaying(false);
                      }
                    }}
                  />
                </article>
              );
            })
          ) : (
            <div className="empty-state">
              <CircleAlert size={24} />
              <span>Select a completed job from the dashboard.</span>
            </div>
          )}
        </div>
      </section>

      <section className={`view ${view === "settings" ? "active" : ""}`}>
        <div className="section-title">
          <h1>System Preferences</h1>
          <p>Configure AI hardware acceleration and model parameters.</p>
        </div>
        <div className="settings-grid">
          <div className="panel">
            <h2>Workspace</h2>
            <div className="engine-card active-gpu">
              <CheckCircle2 size={18} />
              {organization.name}
            </div>
            <div className="engine-card">
              <UserRound size={18} />
              {user.email}
            </div>
            <div className="engine-card">
              <HardDriveDownload size={18} />
              {organization.plan?.name || "Free"} · {organization.plan?.monthly_job_limit ?? 0} jobs/month
            </div>
          </div>
          <div className="panel">
            <h2>Acceleration Engine</h2>
            <div className={`engine-card ${system?.gpu ? "active-gpu" : ""}`}>
              <Cpu size={18} />
              {system?.gpu ? "NVIDIA CUDA (GPU)" : "CPU Mode"}
            </div>
            <div className={`engine-card ${system?.queue_ready ? "active-gpu" : "active-cpu"}`}>
              <CheckCircle2 size={18} />
              Queue {system?.queue_ready ? "ready" : "offline"} · {system?.queue_backend || "unknown"}
            </div>
          </div>
          <div className="panel">
            <h2>Demucs Configuration</h2>
            <label className="control-field">
              <span>Model</span>
              <select value={model} onChange={(event) => setModel(event.target.value)}>
                <option value="htdemucs">htdemucs</option>
                <option value="htdemucs_ft">htdemucs_ft</option>
                <option value="htdemucs_6s">htdemucs_6s</option>
                <option value="mdx_extra">mdx_extra</option>
              </select>
            </label>
            <label className="control-field slider-field">
              <span>
                Segment <b>{segment}s</b>
              </span>
              <input type="range" min="1" max="30" value={segment} onChange={(event) => setSegment(Number(event.target.value))} />
            </label>
            <label className="control-field slider-field">
              <span>
                Overlap <b>{overlap.toFixed(2)}</b>
              </span>
              <input type="range" min="0.1" max="0.9" step="0.05" value={overlap} onChange={(event) => setOverlap(Number(event.target.value))} />
            </label>
            <label className="control-field slider-field">
              <span>
                Shifts <b>{shifts}x</b>
              </span>
              <input type="range" min="1" max="4" value={shifts} onChange={(event) => setShifts(Number(event.target.value))} />
            </label>
          </div>
        </div>
      </section>

      <footer className="player">
        <div className="progress-area" onPointerDown={seekAll}>
          <div className="progress-track">
            <div className="progress-fill" style={{ width: `${playbackRatio * 100}%` }} />
            <div className="progress-thumb" style={{ left: `${playbackRatio * 100}%` }} />
          </div>
          <span className="time-label current">{formatTime(position)}</span>
          <span className="time-label duration">{formatTime(duration)}</span>
        </div>
        <span id="activeStem">{activeStemLabel}</span>
        <button id="playBtn" className={playing ? "playing" : ""} onClick={togglePlayback} title={playing ? "Pause" : "Play"}>
          {playing ? <Pause size={25} fill="currentColor" /> : <Play size={25} fill="currentColor" />}
        </button>
        <label className="master">
          <span className="master-label">
            Master <b>{Math.round(masterVolume * 100)}%</b>
          </span>
          <span className="master-control">
            <SlidersHorizontal size={18} />
            <input type="range" min="0" max="100" value={masterVolume * 100} onChange={(event) => setMasterVolume(Number(event.target.value) / 100)} />
          </span>
        </label>
      </footer>
    </main>
  );
}
