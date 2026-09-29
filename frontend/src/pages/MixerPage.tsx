import { Download, SlidersHorizontal } from "lucide-react";
import type { MutableRefObject } from "react";
import type { Job, Stem } from "../types";
import { CornerWaveBg } from "../components/WaveformEffects";
import { WaveCanvas } from "../components/WaveCanvas";

export interface MixerPageProps {
  isActive: boolean;
  currentJob: Job | null;
  currentStems: Stem[];
  colors: Record<string, string>;
  palette: string[];
  stemUrls: Record<string, string>;
  stemVolumes: Record<string, number>;
  onVolumeChange: (stemName: string, vol: number) => void;
  muted: Record<string, boolean>;
  onToggleMute: (stemName: string) => void;
  solo: string;
  onToggleSolo: (stemName: string) => void;
  onDownloadStem: (stemName: string) => void;
  stemUrlError: string;
  audioRefs: MutableRefObject<Record<string, HTMLAudioElement | null>>;
  onDurationUpdate: (dur: number) => void;
  onPlaybackEnded: () => void;
}

export function MixerPage({
  isActive,
  currentJob,
  currentStems,
  colors,
  palette,
  stemUrls,
  stemVolumes,
  onVolumeChange,
  muted,
  onToggleMute,
  solo,
  onToggleSolo,
  onDownloadStem,
  stemUrlError,
  audioRefs,
  onDurationUpdate,
  onPlaybackEnded
}: MixerPageProps) {
  return (
    <section className={`view mixer-view ${isActive ? "active" : ""}`}>
      <div className="section-title">
        <h1>Stem Mixer</h1>
        <p>
          {currentJob?.status === "done"
            ? "Fine-tune individual components of your track."
            : "A completed job is required for mixing."}
        </p>
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
                      className="neon-slider"
                      min="0"
                      max="100"
                      value={Math.round((stemVolumes[stem.name] ?? 1) * 100)}
                      style={{
                        background: `linear-gradient(to right, ${color} 0%, ${color} ${Math.round(
                          (stemVolumes[stem.name] ?? 1) * 100
                        )}%, rgba(255, 255, 255, 0.12) ${Math.round(
                          (stemVolumes[stem.name] ?? 1) * 100
                        )}%, rgba(255, 255, 255, 0.12) 100%)`
                      }}
                      onChange={(event) =>
                        onVolumeChange(stem.name, Number(event.target.value) / 100)
                      }
                    />
                  </label>
                  <div className="stem-buttons">
                    <button
                      className={`mini-btn ${muted[stem.name] ? "active-mute" : ""}`}
                      onClick={() => onToggleMute(stem.name)}
                      title="Mute"
                    >
                      M
                    </button>
                    <button
                      className={`mini-btn ${solo === stem.name ? "active-solo" : ""}`}
                      onClick={() => onToggleSolo(stem.name)}
                      title="Solo"
                    >
                      S
                    </button>
                    <button
                      className="mini-btn"
                      disabled={!src}
                      onClick={() => onDownloadStem(stem.name)}
                      title="Download"
                    >
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
                  onLoadedMetadata={(event) => {
                    const dur = event.currentTarget?.duration;
                    if (typeof dur === "number" && Number.isFinite(dur) && dur > 0) {
                      onDurationUpdate(dur);
                    }
                  }}
                  onEnded={onPlaybackEnded}
                />
              </article>
            );
          })
        ) : (
          <div className="empty-state">
            <CornerWaveBg />
            <div
              className="upload-circle"
              style={{ width: "56px", height: "56px", marginBottom: "0" }}
            >
              <SlidersHorizontal size={24} className="emerald-icon" />
            </div>
            <strong style={{ fontSize: "16px", color: "#f1f7f3" }}>
              No Stem Track Selected
            </strong>
            <span>
              Select a completed job from the dashboard to launch the multi-track stem mixer.
            </span>
          </div>
        )}
      </div>
    </section>
  );
}
