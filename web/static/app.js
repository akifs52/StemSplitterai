const state = {
  jobId: null,
  job: null,
  audio: null,
  players: {},
  playing: false,
  colors: {},
  stemVolumes: {},
  masterVolume: 0.8,
  muted: {},
  solo: "",
  position: 0,
  duration: 0,
  tick: null,
  lastSyncAt: 0,
};

const palette = ["#FF4D6D", "#4FC3F7", "#FFD166", "#8BE9C1", "#C77DFF", "#FF9F1C", "#2EC4B6", "#E76F51"];
const $ = (id) => document.getElementById(id);

function shuffle(items) {
  const list = items.slice();
  for (let i = list.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [list[i], list[j]] = [list[j], list[i]];
  }
  return list;
}

function popupText(text) {
  const match = (text || "").match(/Initializing Demucs \(([^)]+)\)/);
  return match ? match[1] : (text || "Processing...");
}

function setView(name) {
  document.querySelectorAll(".view").forEach((el) => el.classList.toggle("active", el.id === name));
  document.querySelectorAll(".tab").forEach((el) => el.classList.toggle("active", el.dataset.view === name));
  requestAnimationFrame(redrawPlaybackSurfaces);
}

function normalizeWave(data) {
  const values = (data || []).map((value) => Math.abs(Number(value) || 0));
  if (!values.length) return [];
  const sorted = values.slice().sort((a, b) => a - b);
  const peak = sorted[Math.max(0, Math.floor(sorted.length * 0.95) - 1)] || Math.max(...values) || 1;
  return values.map((value) => Math.min(value / peak, 1));
}

function drawWave(canvas, data, color = "#00e388", position = 0, mode = "center", showProgress = true) {
  const ctx = canvas.getContext("2d");
  const rect = canvas.getBoundingClientRect();
  const ratio = window.devicePixelRatio || 1;
  const cssWidth = Math.max(1, Math.floor(canvas.clientWidth || rect.width || 300));
  const cssHeight = Math.max(1, Math.floor(canvas.clientHeight || rect.height || Number(canvas.getAttribute("height")) || 150));
  canvas.width = Math.floor(cssWidth * ratio);
  canvas.height = Math.floor(cssHeight * ratio);
  ctx.scale(ratio, ratio);
  const w = cssWidth;
  const h = cssHeight;
  ctx.clearRect(0, 0, w, h);
  if (!data || !data.length) {
    ctx.strokeStyle = "rgba(255,255,255,.12)";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(0, h / 2);
    ctx.lineTo(w, h / 2);
    ctx.stroke();
    return;
  }
  const values = normalizeWave(data);
  const gap = values.length > w / 2 ? 0 : 2;
  const barW = Math.max(1, w / values.length - gap);
  const center = h / 2;
  values.forEach((value, index) => {
    const amp = Math.max(Math.min(value, 1), 0.035);
    const barH = mode === "bottom" ? Math.max(1, amp * h * 0.9) : Math.max(1, amp * h * 0.45);
    ctx.fillStyle = !showProgress || index / data.length <= position ? color : "rgba(74,74,74,.45)";
    const x = index * (barW + gap);
    const y = mode === "bottom" ? h - barH : center - barH / 2;
    ctx.globalAlpha = mode === "bottom" ? 0.55 + amp * 0.45 : 1;
    ctx.fillRect(x, y, barW, barH);
  });
  ctx.globalAlpha = 1;
  if (showProgress && position > 0) {
    const x = Math.max(0, Math.min(w, position * w));
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, h);
    ctx.stroke();
    ctx.strokeStyle = "rgba(0,227,136,.15)";
    ctx.lineWidth = 6;
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, h);
    ctx.stroke();
  }
}

function assignColors(stems) {
  const pool = shuffle(palette);
  state.colors = {};
  stems.forEach((stem, index) => state.colors[stem.name] = pool[index % pool.length]);
}

function applyPlayerVolumes() {
  Object.entries(state.players).forEach(([name, player]) => {
    const soloActive = Boolean(state.solo);
    const audible = soloActive ? state.solo === name : !state.muted[name];
    const gain = audible ? (state.stemVolumes[name] ?? 1) : 0;
    player.volume = Math.max(0, Math.min(1, gain * state.masterVolume));
  });
  updateActiveStemLabel();
}

function updateSettingValues() {
  $("segmentValue").textContent = `${$("segment").value}s`;
  $("overlapValue").textContent = Number($("overlap").value).toFixed(2);
  $("shiftsValue").textContent = `${$("shifts").value}x`;
  $("masterValue").textContent = `${$("masterVolume").value}%`;
}

function updateActiveStemLabel() {
  const names = Object.keys(state.players);
  if (!names.length) {
    $("activeStem").textContent = "mix";
    return;
  }
  if (state.solo) {
    $("activeStem").textContent = state.solo;
    return;
  }
  const active = names.filter((name) => !state.muted[name] && (state.stemVolumes[name] ?? 1) > 0);
  $("activeStem").textContent = active.length === 0 ? "muted" : active.length === 1 ? active[0] : "mix";
}

function formatTime(seconds) {
  const safe = Number.isFinite(seconds) ? Math.max(0, Math.floor(seconds)) : 0;
  const mins = Math.floor(safe / 60);
  const secs = safe % 60;
  return `${mins}:${String(secs).padStart(2, "0")}`;
}

function playbackRatio() {
  return state.duration > 0 ? Math.max(0, Math.min(1, state.position / state.duration)) : 0;
}

function primaryPlayer() {
  return Object.values(state.players)[0] || null;
}

function redrawPlaybackSurfaces() {
  const ratio = playbackRatio();
  $("progressFill").style.width = `${ratio * 100}%`;
  $("progressThumb").style.left = `${ratio * 100}%`;
  $("currentTime").textContent = formatTime(state.position);
  $("durationTime").textContent = formatTime(state.duration);
  drawWave($("originalWave"), state.job?.waveform || [], "#00e388", ratio);
  state.job?.stems?.forEach((stem) => {
    const canvas = document.querySelector(`canvas[data-stem="${CSS.escape(stem.name)}"]`);
    if (canvas) drawWave(canvas, state.job.stem_waveforms?.[stem.name] || [], state.colors[stem.name], 1, "bottom", false);
  });
}

function setPlaying(playing) {
  state.playing = playing;
  $("playBtn").textContent = playing ? "pause" : "play_arrow";
  $("playBtn").classList.toggle("playing", playing);
}

function syncPlaybackPosition() {
  const player = primaryPlayer();
  if (!player) return;
  state.position = player.currentTime || 0;
  state.duration = player.duration || state.duration || 0;
  const now = performance.now();
  if (state.playing && now - state.lastSyncAt > 650) {
    Object.values(state.players).forEach((item) => {
      if (item === player || item.paused || !Number.isFinite(item.duration)) return;
      if (Math.abs((item.currentTime || 0) - state.position) > 0.12) {
        item.currentTime = Math.min(state.position, item.duration || state.position);
      }
    });
    state.lastSyncAt = now;
  }
  redrawPlaybackSurfaces();
  if (state.playing) state.tick = requestAnimationFrame(syncPlaybackPosition);
}

function stopPlaybackTick() {
  if (state.tick) cancelAnimationFrame(state.tick);
  state.tick = null;
}

function seekAll(ratio) {
  const target = Math.max(0, Math.min(1, ratio)) * (state.duration || 0);
  Object.values(state.players).forEach((player) => {
    if (Number.isFinite(player.duration) && player.duration > 0) player.currentTime = Math.min(target, player.duration);
  });
  state.position = target;
  redrawPlaybackSurfaces();
}

function renderJob(job) {
  state.job = job;
  redrawPlaybackSurfaces();

  if (job.status !== "done") return;
  assignColors(job.stems);
  state.players = {};
  state.playing = false;
  state.muted = {};
  state.solo = "";
  state.position = 0;
  state.duration = 0;
  stopPlaybackTick();
  setPlaying(false);
  $("stemList").innerHTML = job.stems.map((stem, index) => {
    const color = state.colors[stem.name];
    state.stemVolumes[stem.name] ??= 1;
    const audioUrl = `/api/jobs/${state.jobId}/download/${encodeURIComponent(stem.name)}`;
    return `
      <article class="stem" style="color:${color}">
        <div class="stem-info">
          <div class="stem-label">STEM ${String(index + 1).padStart(2, "0")}</div>
          <div class="stem-name">${stem.name}</div>
        </div>
        <div class="stem-wave-wrap">
          <canvas class="stem-wave" data-stem="${stem.name}" height="64"></canvas>
        </div>
        <div class="stem-actions">
          <label class="gain-control">
            <span>GAIN</span>
            <input data-gain="${stem.name}" type="range" min="0" max="100" value="${state.stemVolumes[stem.name] * 100}">
          </label>
          <div class="stem-buttons">
            <button class="mini-btn" data-mute="${stem.name}" title="Mute">M</button>
            <button class="mini-btn" data-solo="${stem.name}" title="Solo">S</button>
            <a class="mini-btn material" href="${audioUrl}" title="Download">download</a>
          </div>
        </div>
        <audio data-audio="${stem.name}" src="${audioUrl}" preload="auto"></audio>
      </article>`;
  }).join("");
  job.stems.forEach((stem) => {
    const canvas = document.querySelector(`canvas[data-stem="${CSS.escape(stem.name)}"]`);
    drawWave(canvas, job.stem_waveforms?.[stem.name] || [], state.colors[stem.name], 1, "bottom", false);
  });
  document.querySelectorAll("[data-audio]").forEach((audio) => {
    state.players[audio.dataset.audio] = audio;
    audio.addEventListener("loadedmetadata", () => {
      state.duration = Math.max(state.duration || 0, audio.duration || 0);
      redrawPlaybackSurfaces();
    });
    audio.addEventListener("ended", () => {
      if (Object.values(state.players).every((player) => player.ended || player.paused)) {
        stopPlaybackTick();
        setPlaying(false);
        syncPlaybackPosition();
      }
    });
  });
  applyPlayerVolumes();
  bindGainControls();
  setView("mixer");
}

function bindGainControls() {
  document.querySelectorAll("[data-gain]").forEach((input) => {
    input.addEventListener("input", () => {
      const name = input.dataset.gain;
      state.stemVolumes[name] = Number(input.value) / 100;
      applyPlayerVolumes();
    });
  });
  document.querySelectorAll("[data-mute]").forEach((button) => {
    button.addEventListener("click", () => {
      const name = button.dataset.mute;
      state.muted[name] = !state.muted[name];
      button.classList.toggle("active-mute", state.muted[name]);
      applyPlayerVolumes();
    });
  });
  document.querySelectorAll("[data-solo]").forEach((button) => {
    button.addEventListener("click", () => {
      const name = button.dataset.solo;
      state.solo = state.solo === name ? "" : name;
      document.querySelectorAll("[data-solo]").forEach((item) => {
        item.classList.toggle("active-solo", item.dataset.solo === state.solo);
      });
      applyPlayerVolumes();
    });
  });
}

function togglePlayback() {
  const players = Object.values(state.players);
  if (!players.length) return;
  if (state.playing) {
    players.forEach((player) => player.pause());
    stopPlaybackTick();
    setPlaying(false);
    syncPlaybackPosition();
    return;
  }
  const startAt = Math.min(...players.map((player) => player.currentTime || 0));
  state.lastSyncAt = 0;
  Promise.all(players.map((player) => {
    player.currentTime = startAt;
    return player.play().catch(() => null);
  })).then(() => {
    setPlaying(true);
    stopPlaybackTick();
    syncPlaybackPosition();
  });
}

async function pollJob() {
  if (!state.jobId) return;
  const job = await fetch(`/api/jobs/${state.jobId}`).then((r) => r.json());
  $("popupTitle").textContent = popupText(job.stage);
  $("popupSub").textContent = `${job.progress || 0}%`;
  if (job.status === "done" || job.status === "error" || job.status === "cancelled") {
    renderJob(job);
    if (job.status === "done") {
      $("overlay").classList.add("hidden");
      return;
    }
    $("popupTitle").textContent = job.status === "cancelled" ? "Cancelled" : "Separation failed";
    $("popupSub").textContent = job.stage || "Demucs failed.";
    $("errorLog").textContent = job.error_log || "";
    $("errorLog").classList.toggle("visible", Boolean(job.error_log));
    $("cancelBtn").textContent = "Close";
    return;
  }
  setTimeout(pollJob, 700);
}

async function uploadFile(file) {
  const data = new FormData();
  data.append("file", file);
  data.append("model", $("model").value);
  data.append("segment", $("segment").value);
  data.append("overlap", $("overlap").value);
  data.append("shifts", $("shifts").value);
  $("overlay").classList.remove("hidden");
  $("popupTitle").textContent = "Preparing audio file...";
  $("popupSub").textContent = "Uploading...";
  $("errorLog").textContent = "";
  $("errorLog").classList.remove("visible");
  $("cancelBtn").textContent = "Cancel";
  const result = await fetch("/api/jobs", { method: "POST", body: data }).then((r) => r.json());
  state.jobId = result.job_id;
  pollJob();
}

document.querySelectorAll(".tab").forEach((tab) => tab.addEventListener("click", () => setView(tab.dataset.view)));
$("fileInput").addEventListener("change", (event) => event.target.files[0] && uploadFile(event.target.files[0]));
$("dropZone").addEventListener("dragover", (event) => event.preventDefault());
$("dropZone").addEventListener("drop", (event) => {
  event.preventDefault();
  const file = event.dataTransfer.files[0];
  if (file) uploadFile(file);
});
$("cancelBtn").addEventListener("click", async () => {
  if ($("cancelBtn").textContent === "Close") {
    $("overlay").classList.add("hidden");
    return;
  }
  if (!state.jobId) return;
  $("popupTitle").textContent = "Cancelling...";
  await fetch(`/api/jobs/${state.jobId}/cancel`, { method: "POST" });
});
$("playBtn").addEventListener("click", togglePlayback);
$("progressArea").addEventListener("click", (event) => {
  const rect = $("progressArea").getBoundingClientRect();
  seekAll((event.clientX - rect.left) / rect.width);
});
$("progressArea").addEventListener("pointerdown", (event) => {
  $("progressArea").setPointerCapture(event.pointerId);
  seekAll((event.clientX - $("progressArea").getBoundingClientRect().left) / $("progressArea").getBoundingClientRect().width);
});
$("progressArea").addEventListener("pointermove", (event) => {
  if (event.buttons !== 1) return;
  const rect = $("progressArea").getBoundingClientRect();
  seekAll((event.clientX - rect.left) / rect.width);
});
$("masterVolume").addEventListener("input", () => {
  state.masterVolume = Number($("masterVolume").value) / 100;
  updateSettingValues();
  applyPlayerVolumes();
});
["segment", "overlap", "shifts"].forEach((id) => $(id).addEventListener("input", updateSettingValues));

fetch("/api/system").then((r) => r.json()).then((info) => {
  $("deviceBadge").textContent = info.device;
  $("gpuCard").classList.toggle("active-gpu", info.gpu);
  $("cpuCard").classList.toggle("active-cpu", !info.gpu);
});

redrawPlaybackSurfaces();
updateSettingValues();
