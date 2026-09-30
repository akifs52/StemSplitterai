import { HardDriveDownload, LogOut, Music2, Settings, SlidersHorizontal, UploadCloud, WifiOff } from "lucide-react";
import type { InstallPromptEvent, SystemInfo, ViewName } from "../types";

export interface HeaderProps {
  view: ViewName;
  onNavigate: (view: ViewName) => void;
  online: boolean;
  installPrompt: InstallPromptEvent | null;
  onInstallApp: () => void;
  system: SystemInfo | null;
  onLogout: () => void;
}

export function Header({
  view,
  onNavigate,
  online,
  installPrompt,
  onInstallApp,
  system,
  onLogout
}: HeaderProps) {
  return (
    <header className="topbar">
      <div className="brand-lockup" onClick={() => onNavigate("dashboard")} style={{ cursor: "pointer" }}>
        <Music2 size={24} />
        <span>StemSplit AI</span>
      </div>
      <nav className="tabs" aria-label="Main Navigation">
        <button
          className={view === "dashboard" ? "active" : ""}
          onClick={() => onNavigate("dashboard")}
          title="Dashboard"
          aria-label="Dashboard"
        >
          <UploadCloud size={16} />
          <span className="tab-label">Dashboard</span>
        </button>
        <button
          className={view === "mixer" ? "active" : ""}
          onClick={() => onNavigate("mixer")}
          title="Mixer"
          aria-label="Mixer"
        >
          <SlidersHorizontal size={16} />
          <span className="tab-label">Mixer</span>
        </button>
        <button
          className={view === "settings" ? "active" : ""}
          onClick={() => onNavigate("settings")}
          title="Settings"
          aria-label="Settings"
        >
          <Settings size={16} />
          <span className="tab-label">Settings</span>
        </button>
      </nav>
      <div className="top-actions">
        {!online && <WifiOff className="offline-icon" size={18} />}
        {installPrompt && (
          <button className="icon-btn" onClick={onInstallApp} title="Install app">
            <HardDriveDownload size={18} />
          </button>
        )}
        <div className="device-badge">{system?.device || "CPU"}</div>
        <button className="icon-btn" onClick={onLogout} title="Log out">
          <LogOut size={18} />
        </button>
      </div>
    </header>
  );
}
