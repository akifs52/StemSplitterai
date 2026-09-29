import {
  ChevronDown,
  ChevronRight,
  FileAudio,
  Folder,
  History,
  Loader2,
  RefreshCw,
  UploadCloud,
  X
} from "lucide-react";
import type { Job } from "../types";
import { CornerWaveBg, PanelWavesBg } from "../components/WaveformEffects";
import { WaveformIcon } from "../components/Icons";
import { WaveCanvas } from "../components/WaveCanvas";

export interface DashboardPageProps {
  isActive: boolean;
  organizationName: string;
  uploading: boolean;
  uploadError: string;
  onUploadFile: (file: File) => void;
  currentJob: Job | null;
  activeJobRunning: boolean;
  onCancelJob: () => void;
  playbackRatio: number;
  jobs: Job[];
  onLoadJob: (jobId: string, switchToMixer?: boolean) => void;
  onRefreshJobs: () => void;
  formatBytes: (bytes: number) => string;
  statusLabel: (job: Job) => string;
}

export function DashboardPage({
  isActive,
  organizationName,
  uploading,
  uploadError,
  onUploadFile,
  currentJob,
  activeJobRunning,
  onCancelJob,
  playbackRatio,
  jobs,
  onLoadJob,
  onRefreshJobs,
  formatBytes,
  statusLabel
}: DashboardPageProps) {
  return (
    <section className={`view dashboard-view ${isActive ? "active" : ""}`}>
      <div className="section-title">
        <h1>Source Separation</h1>
        <p>{organizationName || "Workspace"} workspace</p>
      </div>

      <div className="dashboard-grid">
        <label
          className="drop-zone"
          onDragOver={(event) => event.preventDefault()}
          onDrop={(event) => {
            event.preventDefault();
            const file = event.dataTransfer.files[0];
            if (file) {
              onUploadFile(file);
            }
          }}
        >
          <input
            type="file"
            accept="audio/*"
            onChange={(event) => event.target.files?.[0] && onUploadFile(event.target.files[0])}
          />
          <PanelWavesBg />
          <div className="upload-circle">
            {uploading ? (
              <Loader2 className="spin upload-icon" size={34} />
            ) : (
              <UploadCloud className="upload-icon" size={34} />
            )}
          </div>
          <strong className="drop-title">
            Drop or <span className="highlight-green">choose audio</span>
          </strong>
          <small className="drop-sub">MP3, WAV, FLAC, M4A, OGG</small>
          <div className="browse-files-pill">
            <Folder size={15} />
            <span>Browse Files</span>
            <ChevronRight size={14} />
          </div>
        </label>

        <aside className="job-panel">
          <CornerWaveBg />
          <div className="panel-head">
            <strong>
              <WaveformIcon />
              <span>Current Job</span>
            </strong>
            <span className={`status-pill ${currentJob?.status || "idle"}`}>
              <span className="pulse-dot" />
              {currentJob
                ? currentJob.status === "running"
                  ? `${currentJob.progress || 0}%`
                  : currentJob.status
                : "Idle"}
            </span>
          </div>
          <div className="status-card">
            <div className={`status-dot ${currentJob?.status || "idle"}`} />
            <div>
              <strong>{currentJob ? statusLabel(currentJob) : "No active job"}</strong>
              <small>{currentJob?.source_filename || "Upload a file to start."}</small>
            </div>
          </div>
          <div className="progress-bar">
            <span style={{ width: `${currentJob?.progress || 0}%` }} />
          </div>
          {activeJobRunning && (
            <button className="danger-btn" onClick={onCancelJob}>
              <X size={16} />
              Cancel job
            </button>
          )}
          {uploadError && <p className="error-line">{uploadError}</p>}
        </aside>
      </div>

      <div className="wave-panel">
        <div className="panel-head">
          <strong>
            <WaveformIcon />
            <span>Original Waveform</span>
          </strong>
          <div className="source-pill">
            <FileAudio size={14} />
            <span>{currentJob?.source_filename || "No source loaded"}</span>
            <ChevronDown size={14} />
          </div>
        </div>
        <div className="wave-wrapper">
          <WaveCanvas
            data={currentJob?.waveform || []}
            color="#00FFA3"
            position={playbackRatio}
            className="original-wave"
          />
          {(!currentJob || !currentJob.waveform || currentJob.waveform.length === 0) && (
            <div className="wave-empty-overlay">
              <div className="wave-center-line" />
              <span className="wave-empty-text">No file loaded</span>
            </div>
          )}
        </div>
      </div>

      <div className="history-panel">
        <div className="panel-head">
          <strong>
            <History size={17} className="emerald-icon" />
            <span>Job History</span>
          </strong>
          <button className="refresh-pill-btn" onClick={onRefreshJobs} type="button">
            <RefreshCw size={13} />
            <span>Refresh</span>
          </button>
        </div>
        {jobs.length === 0 ? (
          <div className="history-empty">No jobs yet.</div>
        ) : (
          <div className="job-list">
            {jobs.map((job) => (
              <button
                key={job.id}
                className={`job-row ${currentJob?.id === job.id ? "selected" : ""}`}
                onClick={() => onLoadJob(job.id, job.status === "done")}
              >
                <span>
                  <strong>{job.source_filename}</strong>
                  <small>
                    {formatBytes(job.source_size_bytes)} · {job.model}
                  </small>
                </span>
                <span className={`job-status ${job.status}`}>{job.status}</span>
              </button>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
