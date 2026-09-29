import { Pause, Play, Volume2 } from "lucide-react";
import type { PointerEvent } from "react";
import { PlayerCenterWaves } from "./WaveformEffects";

export interface PlayerProps {
  playing: boolean;
  onTogglePlayback: () => void;
  position: number;
  duration: number;
  playbackRatio: number;
  onSeek: (event: PointerEvent<HTMLDivElement>) => void;
  activeStemLabel: string;
  masterVolume: number;
  onVolumeChange: (volume: number) => void;
  formatTime: (seconds: number) => string;
}

export function Player({
  playing,
  onTogglePlayback,
  position,
  duration,
  playbackRatio,
  onSeek,
  activeStemLabel,
  masterVolume,
  onVolumeChange,
  formatTime
}: PlayerProps) {
  return (
    <footer className="player">
      <div className="progress-area" onPointerDown={onSeek}>
        <div className="progress-track">
          <div className="progress-fill" style={{ width: `${playbackRatio * 100}%` }} />
          <div className="progress-thumb" style={{ left: `${playbackRatio * 100}%` }} />
        </div>
        <span className="time-label current">{formatTime(position)}</span>
        <span className="time-label duration">{formatTime(duration)}</span>
      </div>

      <div className="player-left-side">
        <span className="player-status-badge">
          <span className="status-live-dot" />
          <span className="status-live-text">{playing ? activeStemLabel : "Ready"}</span>
        </span>
      </div>

      <div className="player-center-wrap">
        <PlayerCenterWaves playing={playing} />
        <button
          id="playBtn"
          className={playing ? "playing" : ""}
          onClick={onTogglePlayback}
          title={playing ? "Pause" : "Play"}
        >
          {playing ? (
            <Pause size={24} fill="currentColor" />
          ) : (
            <Play size={24} fill="currentColor" style={{ marginLeft: "3px" }} />
          )}
        </button>
      </div>

      <div className="player-right-side">
        <div className="master-volume-box">
          <Volume2 size={18} className="vol-icon" />
          <span className="vol-label">Master</span>
          <div className="volume-slider-wrap">
            <input
              type="range"
              className="neon-slider"
              min="0"
              max="100"
              value={Math.round(masterVolume * 100)}
              style={{
                background: `linear-gradient(to right, #00FFA3 0%, #00FFA3 ${Math.round(masterVolume * 100)}%, rgba(255, 255, 255, 0.12) ${Math.round(masterVolume * 100)}%, rgba(255, 255, 255, 0.12) 100%)`
              }}
              onChange={(event) => onVolumeChange(Number(event.target.value) / 100)}
            />
          </div>
          <span className="vol-pct">{Math.round(masterVolume * 100)}%</span>
        </div>
      </div>
    </footer>
  );
}
