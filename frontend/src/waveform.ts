export function normalizeWave(data: number[]): number[] {
  const values = (data || []).map((value) => Math.abs(Number(value) || 0));
  if (!values.length) {
    return [];
  }
  const sorted = values.slice().sort((a, b) => a - b);
  const peak = sorted[Math.max(0, Math.floor(sorted.length * 0.95) - 1)] || Math.max(...values) || 1;
  return values.map((value) => Math.min(value / peak, 1));
}

export function drawWave(
  canvas: HTMLCanvasElement,
  data: number[],
  color = "#00e388",
  position = 0,
  mode: "center" | "bottom" = "center",
  showProgress = true
): void {
  const ctx = canvas.getContext("2d");
  if (!ctx) {
    return;
  }
  const rect = canvas.getBoundingClientRect();
  const ratio = window.devicePixelRatio || 1;
  const cssWidth = Math.max(1, Math.floor(canvas.clientWidth || rect.width || 300));
  const cssHeight = Math.max(1, Math.floor(canvas.clientHeight || rect.height || Number(canvas.getAttribute("height")) || 150));
  canvas.width = Math.floor(cssWidth * ratio);
  canvas.height = Math.floor(cssHeight * ratio);
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  ctx.clearRect(0, 0, cssWidth, cssHeight);

  if (!data.length) {
    ctx.strokeStyle = "rgba(255,255,255,.12)";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(0, cssHeight / 2);
    ctx.lineTo(cssWidth, cssHeight / 2);
    ctx.stroke();
    return;
  }

  const values = normalizeWave(data);
  const gap = values.length > cssWidth / 2 ? 0 : 2;
  const barWidth = Math.max(1, cssWidth / values.length - gap);
  const center = cssHeight / 2;
  values.forEach((value, index) => {
    const amp = Math.max(Math.min(value, 1), 0.035);
    const barHeight = mode === "bottom" ? Math.max(1, amp * cssHeight * 0.9) : Math.max(1, amp * cssHeight * 0.45);
    ctx.fillStyle = !showProgress || index / data.length <= position ? color : "rgba(74,74,74,.45)";
    const x = index * (barWidth + gap);
    const y = mode === "bottom" ? cssHeight - barHeight : center - barHeight / 2;
    ctx.globalAlpha = mode === "bottom" ? 0.55 + amp * 0.45 : 1;
    ctx.fillRect(x, y, barWidth, barHeight);
  });
  ctx.globalAlpha = 1;

  if (showProgress && position > 0) {
    const x = Math.max(0, Math.min(cssWidth, position * cssWidth));
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, cssHeight);
    ctx.stroke();
    ctx.strokeStyle = "rgba(0,227,136,.15)";
    ctx.lineWidth = 6;
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, cssHeight);
    ctx.stroke();
  }
}

