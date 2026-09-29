import { CheckCircle2, Cpu, HardDriveDownload, Settings, UserRound } from "lucide-react";
import type { Organization, SystemInfo, User } from "../types";
import { CornerWaveBg } from "../components/WaveformEffects";
import { WaveformIcon } from "../components/Icons";

export interface SettingsPageProps {
  isActive: boolean;
  organization: Organization | null;
  user: User | null;
  system: SystemInfo | null;
  model: string;
  onModelChange: (model: string) => void;
  segment: number;
  onSegmentChange: (segment: number) => void;
  overlap: number;
  onOverlapChange: (overlap: number) => void;
  shifts: number;
  onShiftsChange: (shifts: number) => void;
}

export function SettingsPage({
  isActive,
  organization,
  user,
  system,
  model,
  onModelChange,
  segment,
  onSegmentChange,
  overlap,
  onOverlapChange,
  shifts,
  onShiftsChange
}: SettingsPageProps) {
  return (
    <section className={`view settings-view ${isActive ? "active" : ""}`}>
      <div className="section-title">
        <h1>System Preferences</h1>
        <p>Configure AI hardware acceleration and model parameters.</p>
      </div>

      <div className="settings-grid">
        <div className="panel">
          <CornerWaveBg />
          <h2>
            <WaveformIcon />
            <span>Workspace</span>
          </h2>
          <div className="engine-card active-gpu">
            <CheckCircle2 size={18} />
            {organization?.name || "Workspace"}
          </div>
          <div className="engine-card">
            <UserRound size={18} />
            {user?.email || "User"}
          </div>
          <div className="engine-card">
            <HardDriveDownload size={18} />
            {organization?.plan?.name || "Free"} ·{" "}
            {organization?.plan?.monthly_job_limit ?? 0} jobs/month
          </div>
        </div>

        <div className="panel">
          <CornerWaveBg />
          <h2>
            <Cpu size={18} className="emerald-icon" />
            <span>Acceleration Engine</span>
          </h2>
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
          <CornerWaveBg />
          <h2>
            <Settings size={18} className="emerald-icon" />
            <span>Demucs Configuration</span>
          </h2>
          <label className="control-field">
            <span>Model</span>
            <select value={model} onChange={(event) => onModelChange(event.target.value)}>
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
            <input
              type="range"
              className="neon-slider"
              min="1"
              max="30"
              value={segment}
              style={{
                background: `linear-gradient(to right, #00FFA3 0%, #00FFA3 ${Math.round(
                  ((segment - 1) / 29) * 100
                )}%, rgba(255, 255, 255, 0.12) ${Math.round(
                  ((segment - 1) / 29) * 100
                )}%, rgba(255, 255, 255, 0.12) 100%)`
              }}
              onChange={(event) => onSegmentChange(Number(event.target.value))}
            />
          </label>
          <label className="control-field slider-field">
            <span>
              Overlap <b>{overlap.toFixed(2)}</b>
            </span>
            <input
              type="range"
              className="neon-slider"
              min="0.1"
              max="0.9"
              step="0.05"
              value={overlap}
              style={{
                background: `linear-gradient(to right, #00FFA3 0%, #00FFA3 ${Math.round(
                  ((overlap - 0.1) / 0.8) * 100
                )}%, rgba(255, 255, 255, 0.12) ${Math.round(
                  ((overlap - 0.1) / 0.8) * 100
                )}%, rgba(255, 255, 255, 0.12) 100%)`
              }}
              onChange={(event) => onOverlapChange(Number(event.target.value))}
            />
          </label>
          <label className="control-field slider-field">
            <span>
              Shifts <b>{shifts}x</b>
            </span>
            <input
              type="range"
              className="neon-slider"
              min="1"
              max="4"
              value={shifts}
              style={{
                background: `linear-gradient(to right, #00FFA3 0%, #00FFA3 ${Math.round(
                  ((shifts - 1) / 3) * 100
                )}%, rgba(255, 255, 255, 0.12) ${Math.round(
                  ((shifts - 1) / 3) * 100
                )}%, rgba(255, 255, 255, 0.12) 100%)`
              }}
              onChange={(event) => onShiftsChange(Number(event.target.value))}
            />
          </label>
        </div>
      </div>
    </section>
  );
}
