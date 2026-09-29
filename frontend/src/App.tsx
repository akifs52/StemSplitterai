import { FormEvent, PointerEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";

import { ApiError, api, clearStoredToken, getStoredToken, storeToken } from "./api";
import type { AuthProviders, InstallPromptEvent, Job, Organization, SystemInfo, User, ViewName } from "./types";
import { getViewFromPath, syncRoute } from "./router";

import { Header } from "./components/Header";
import { Player } from "./components/Player";
import { CornerWaveBg } from "./components/WaveformEffects";

import { LoginPage } from "./pages/LoginPage";
import { RegisterPage } from "./pages/RegisterPage";
import { DashboardPage } from "./pages/DashboardPage";
import { MixerPage } from "./pages/MixerPage";
import { SettingsPage } from "./pages/SettingsPage";

const palette = ["#ff4d6d", "#4fc3f7", "#ffd166", "#8be9c1", "#c77dff", "#ff9f1c", "#2ec4b6", "#e76f51"];
const terminalStatuses = new Set(["done", "error", "cancelled"]);

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
    window.history.replaceState(null, "", window.location.pathname || "/");
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

export function App() {
  const [token, setToken] = useState<string>(() => initialOAuth.token || getStoredToken());
  const [user, setUser] = useState<User | null>(null);
  const [organization, setOrganization] = useState<Organization | null>(null);
  const [system, setSystem] = useState<SystemInfo | null>(null);
  const [authProviders, setAuthProviders] = useState<AuthProviders>({ google: false, apple: false });
  const [bootstrapping, setBootstrapping] = useState(true);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [organizationName, setOrganizationName] = useState("");
  const [authError, setAuthError] = useState(initialOAuth.error);
  const [authBusy, setAuthBusy] = useState(false);

  const [view, setView] = useState<ViewName>(() => getViewFromPath(window.location.pathname));
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

  const isAuthenticated = Boolean(token && user && organization);
  const currentStems = currentJob?.stems || [];
  const playbackRatio = duration > 0 ? Math.max(0, Math.min(1, position / duration)) : 0;
  const activeJobRunning = Boolean(currentJob && !terminalStatuses.has(currentJob.status));

  const navigate = useCallback((nextView: ViewName) => {
    setView(nextView);
    syncRoute(nextView, false);
  }, []);

  useEffect(() => {
    syncRoute(view, true);
    const handlePopState = () => {
      const targetView = getViewFromPath(window.location.pathname);
      setView(targetView);
      syncRoute(targetView, true);
    };
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, [view]);

  // Route protection & auth redirect
  useEffect(() => {
    if (!bootstrapping) {
      if (!isAuthenticated) {
        if (view !== "login" && view !== "register") {
          navigate("login");
        }
      } else {
        if (view === "login" || view === "register") {
          navigate("dashboard");
        }
      }
    }
  }, [bootstrapping, isAuthenticated, navigate, view]);

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
      navigate("login");
      return true;
    }
    return false;
  }, [navigate]);

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
          navigate("mixer");
        }
      } catch (error) {
        handleUnauthorized(error);
      }
    },
    [handleUnauthorized, navigate, token, upsertJob]
  );

  const refreshJobs = useCallback(
    async (authToken = token) => {
      if (!authToken) {
        return;
      }
      try {
        const rows = await api.listJobs(authToken);
        setJobs(rows);
        setCurrentJob((previous) => {
          if (!previous) {
            return null;
          }
          return rows.find((item) => item.id === previous.id) || null;
        });
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
          navigate("mixer");
        }
      } catch (error) {
        handleUnauthorized(error);
      }
    }, 1000);
    return () => window.clearInterval(timer);
  }, [currentJob, handleUnauthorized, navigate, token, upsertJob]);

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
      const players = Object.values(audioRefs.current).filter(
        (p): p is HTMLAudioElement => Boolean(p && typeof p.duration === "number")
      );
      const primary = players[0];
      if (primary && Number.isFinite(primary.currentTime)) {
        setPosition(primary.currentTime || 0);
        const maxDur = Math.max(
          ...players.map((p) => (p && Number.isFinite(p.duration) ? p.duration : 0)),
          0
        );
        if (maxDur > 0) {
          setDuration(maxDur);
        }
        players.forEach((player) => {
          if (player && player !== primary && !player.paused && Number.isFinite(player.duration)) {
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

  const submitLogin = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setAuthBusy(true);
    setAuthError("");
    try {
      const response = await api.login(email, password);
      storeToken(response.access_token);
      setToken(response.access_token);
      setUser(response.user);
      setOrganization(response.organization);
      navigate("dashboard");
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : "Authentication failed");
    } finally {
      setAuthBusy(false);
    }
  };

  const submitRegister = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setAuthBusy(true);
    setAuthError("");
    try {
      const response = await api.register(email, password, fullName, organizationName);
      storeToken(response.access_token);
      setToken(response.access_token);
      setUser(response.user);
      setOrganization(response.organization);
      navigate("dashboard");
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : "Registration failed");
    } finally {
      setAuthBusy(false);
    }
  };

  const startOAuth = (provider: "google" | "apple") => {
    setAuthError("");
    window.location.href = api.oauthStartUrl(provider, view === "register" ? "register" : "login");
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
    navigate("login");
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
      navigate("dashboard");
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
    const rect = event.currentTarget?.getBoundingClientRect();
    if (!rect || rect.width <= 0) {
      return;
    }
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
          <CornerWaveBg />
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

  if (!isAuthenticated) {
    if (view === "register") {
      return (
        <RegisterPage
          email={email}
          onEmailChange={setEmail}
          password={password}
          onPasswordChange={setPassword}
          fullName={fullName}
          onFullNameChange={setFullName}
          organizationName={organizationName}
          onOrganizationNameChange={setOrganizationName}
          authError={authError}
          authBusy={authBusy}
          authProviders={authProviders}
          onSubmit={submitRegister}
          onStartOAuth={startOAuth}
          onNavigateToLogin={() => {
            setAuthError("");
            navigate("login");
          }}
          online={online}
        />
      );
    }
    return (
      <LoginPage
        email={email}
        onEmailChange={setEmail}
        password={password}
        onPasswordChange={setPassword}
        authError={authError}
        authBusy={authBusy}
        authProviders={authProviders}
        onSubmit={submitLogin}
        onStartOAuth={startOAuth}
        onNavigateToRegister={() => {
          setAuthError("");
          navigate("register");
        }}
        online={online}
      />
    );
  }

  return (
    <main className="app-shell">
      <Header
        view={view}
        onNavigate={navigate}
        online={online}
        installPrompt={installPrompt}
        onInstallApp={installApp}
        system={system}
        onLogout={logout}
      />

      <DashboardPage
        isActive={view === "dashboard"}
        organizationName={organization?.name || "Workspace"}
        uploading={uploading}
        uploadError={uploadError}
        onUploadFile={uploadFile}
        currentJob={currentJob}
        activeJobRunning={activeJobRunning}
        onCancelJob={cancelCurrentJob}
        playbackRatio={playbackRatio}
        jobs={jobs}
        onLoadJob={(id, switchToMixer) => loadJob(id, switchToMixer)}
        onRefreshJobs={() => refreshJobs()}
        formatBytes={formatBytes}
        statusLabel={statusLabel}
      />

      <MixerPage
        isActive={view === "mixer"}
        currentJob={currentJob}
        currentStems={currentStems}
        colors={colors}
        palette={palette}
        stemUrls={stemUrls}
        stemVolumes={stemVolumes}
        onVolumeChange={(stemName, vol) =>
          setStemVolumes((prev) => ({ ...prev, [stemName]: vol }))
        }
        muted={muted}
        onToggleMute={(stemName) =>
          setMuted((prev) => ({ ...prev, [stemName]: !prev[stemName] }))
        }
        solo={solo}
        onToggleSolo={(stemName) =>
          setSolo((prev) => (prev === stemName ? "" : stemName))
        }
        onDownloadStem={downloadStem}
        stemUrlError={stemUrlError}
        audioRefs={audioRefs}
        onDurationUpdate={(dur) => setDuration((prev) => Math.max(prev, dur))}
        onPlaybackEnded={() => {
          const players = Object.values(audioRefs.current).filter(
            (p): p is HTMLAudioElement => Boolean(p)
          );
          if (players.length > 0 && players.every((p) => Boolean(p.paused || p.ended))) {
            setPlaying(false);
          }
        }}
      />

      <SettingsPage
        isActive={view === "settings"}
        organization={organization}
        user={user}
        system={system}
        model={model}
        onModelChange={setModel}
        segment={segment}
        onSegmentChange={setSegment}
        overlap={overlap}
        onOverlapChange={setOverlap}
        shifts={shifts}
        onShiftsChange={setShifts}
      />

      <Player
        playing={playing}
        onTogglePlayback={togglePlayback}
        position={position}
        duration={duration}
        playbackRatio={playbackRatio}
        onSeek={seekAll}
        activeStemLabel={activeStemLabel}
        masterVolume={masterVolume}
        onVolumeChange={setMasterVolume}
        formatTime={formatTime}
      />
    </main>
  );
}
