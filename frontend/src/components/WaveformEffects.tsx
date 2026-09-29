import { useEffect, useRef } from "react";

export function PanelWavesBg() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animId: number;
    let isVisible = true;
    const handleVis = () => {
      isVisible = !document.hidden;
    };
    document.addEventListener("visibilitychange", handleVis);

    let width = 0;
    let height = 0;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);

    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      width = rect.width;
      height = rect.height;
      canvas.width = Math.floor(width * dpr);
      canvas.height = Math.floor(height * dpr);
    };
    resize();

    const observer = new ResizeObserver(resize);
    observer.observe(canvas);

    const render = (time: number) => {
      if (isVisible && width > 0 && height > 0) {
        ctx.save();
        ctx.scale(dpr, dpr);
        ctx.clearRect(0, 0, width, height);

        const baseline = height * 0.68;
        const t = time * 0.001;

        // Wave 1: Back wave with glowing gradient fill
        ctx.beginPath();
        ctx.moveTo(0, height);
        for (let x = 0; x <= width; x += 4) {
          const y =
            baseline +
            8 +
            Math.sin(x * 0.0035 + t * 1.3) * 16 +
            Math.sin(x * 0.0075 - t * 1.8) * 10 +
            Math.cos(x * 0.014 + t * 2.4) * 6;
          ctx.lineTo(x, y);
        }
        ctx.lineTo(width, height);
        ctx.closePath();

        const grad = ctx.createLinearGradient(0, baseline - 25, 0, height);
        grad.addColorStop(0, "rgba(0, 255, 163, 0.28)");
        grad.addColorStop(0.5, "rgba(0, 227, 136, 0.09)");
        grad.addColorStop(1, "rgba(0, 255, 163, 0.0)");
        ctx.fillStyle = grad;
        ctx.fill();

        ctx.strokeStyle = "rgba(0, 255, 163, 0.35)";
        ctx.lineWidth = 1.2;
        ctx.stroke();

        // Wave 2: Middle echo wave
        ctx.beginPath();
        for (let x = 0; x <= width; x += 4) {
          const y =
            baseline +
            Math.sin(x * 0.0042 + t * 1.6 + 1.5) * 20 +
            Math.cos(x * 0.0091 - t * 2.1 + 0.8) * 13 +
            Math.sin(x * 0.017 + t * 3.0) * 7;
          if (x === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.strokeStyle = "rgba(0, 255, 163, 0.55)";
        ctx.lineWidth = 1.4;
        ctx.shadowColor = "#00FFA3";
        ctx.shadowBlur = 6;
        ctx.stroke();

        // Wave 3: Front primary neon ribbon with strong glow
        ctx.beginPath();
        for (let x = 0; x <= width; x += 4) {
          const y =
            baseline -
            8 +
            Math.sin(x * 0.0049 - t * 1.7) * 24 +
            Math.sin(x * 0.0105 + t * 2.3 + 2.3) * 14 +
            Math.cos(x * 0.019 - t * 3.3) * 8;
          if (x === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.strokeStyle = "#00FFA3";
        ctx.lineWidth = 2.2;
        ctx.shadowColor = "#00FFA3";
        ctx.shadowBlur = 14;
        ctx.stroke();

        // Wave 4: Delicate ethereal ripple
        ctx.beginPath();
        for (let x = 0; x <= width; x += 6) {
          const y =
            baseline -
            16 +
            Math.sin(x * 0.0031 + t * 0.9) * 18 +
            Math.cos(x * 0.0083 + t * 2.0 + 1.1) * 10;
          if (x === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.strokeStyle = "rgba(0, 255, 163, 0.25)";
        ctx.lineWidth = 1.0;
        ctx.shadowBlur = 0;
        ctx.stroke();

        ctx.restore();
      }
      animId = requestAnimationFrame(render);
    };

    animId = requestAnimationFrame(render);

    return () => {
      cancelAnimationFrame(animId);
      observer.disconnect();
      document.removeEventListener("visibilitychange", handleVis);
    };
  }, []);

  return <canvas ref={canvasRef} className="panel-waves-bg" />;
}

export function CornerWaveBg() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const seed = useRef(Math.random() * 500 + 100);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animId: number;
    let isVisible = true;
    const handleVis = () => {
      isVisible = !document.hidden;
    };
    document.addEventListener("visibilitychange", handleVis);

    let width = 0;
    let height = 0;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);

    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      width = rect.width;
      height = rect.height;
      canvas.width = Math.floor(width * dpr);
      canvas.height = Math.floor(height * dpr);
    };
    resize();

    const observer = new ResizeObserver(resize);
    observer.observe(canvas);

    const s = seed.current;

    const render = (time: number) => {
      if (isVisible && width > 0 && height > 0) {
        ctx.save();
        ctx.scale(dpr, dpr);
        ctx.clearRect(0, 0, width, height);

        const t = (time + s * 100) * 0.001;

        // Primary curve points with organic drift
        const startX = width * 0.15 + Math.sin(t * 1.3) * 12;
        const startY = height;
        const cp1X = width * 0.35 + Math.cos(t * 1.7) * 16;
        const cp1Y = height * 0.42 + Math.sin(t * 2.1) * 14;
        const cp2X = width * 0.65 + Math.sin(t * 1.5 + 1.2) * 18;
        const cp2Y = height * 0.85 + Math.cos(t * 2.3 + 0.8) * 12;
        const endX = width;
        const endY = height * 0.36 + Math.sin(t * 1.6 + 2.0) * 14;

        // Gradient fill under primary ribbon
        ctx.beginPath();
        ctx.moveTo(startX, startY);
        ctx.bezierCurveTo(cp1X, cp1Y, cp2X, cp2Y, endX, endY);
        ctx.lineTo(width, height);
        ctx.closePath();

        const grad = ctx.createLinearGradient(0, height, width, 0);
        grad.addColorStop(0, "rgba(0, 255, 163, 0.4)");
        grad.addColorStop(0.6, "rgba(0, 227, 136, 0.12)");
        grad.addColorStop(1, "rgba(0, 255, 163, 0.0)");
        ctx.fillStyle = grad;
        ctx.fill();

        // Primary ribbon stroke with neon glow
        ctx.beginPath();
        ctx.moveTo(startX, startY);
        ctx.bezierCurveTo(cp1X, cp1Y, cp2X, cp2Y, endX, endY);
        ctx.strokeStyle = "#00FFA3";
        ctx.lineWidth = 2.0;
        ctx.shadowColor = "#00FFA3";
        ctx.shadowBlur = 10;
        ctx.stroke();

        // Secondary echo ribbon
        const eStartX = width * 0.3 + Math.sin(t * 1.1 + 0.5) * 10;
        const eCp1X = width * 0.48 + Math.cos(t * 1.4 + 1.0) * 14;
        const eCp1Y = height * 0.6 + Math.sin(t * 1.8 + 0.4) * 12;
        const eCp2X = width * 0.72 + Math.sin(t * 1.6 + 2.0) * 14;
        const eCp2Y = height * 0.88 + Math.cos(t * 1.9 + 1.2) * 10;
        const eEndY = height * 0.55 + Math.sin(t * 1.4 + 1.5) * 12;

        ctx.beginPath();
        ctx.moveTo(eStartX, height);
        ctx.bezierCurveTo(eCp1X, eCp1Y, eCp2X, eCp2Y, width, eEndY);
        ctx.strokeStyle = "rgba(0, 255, 163, 0.45)";
        ctx.lineWidth = 1.2;
        ctx.shadowBlur = 4;
        ctx.stroke();

        // Tertiary faint ripple
        const tStartX = width * 0.45 + Math.sin(t * 0.9 + 1.2) * 8;
        const tCp1X = width * 0.6 + Math.cos(t * 1.2) * 10;
        const tCp1Y = height * 0.75 + Math.sin(t * 1.5) * 8;
        const tEndY = height * 0.72 + Math.sin(t * 1.2 + 0.8) * 8;

        ctx.beginPath();
        ctx.moveTo(tStartX, height);
        ctx.bezierCurveTo(tCp1X, tCp1Y, width * 0.85, height * 0.92, width, tEndY);
        ctx.strokeStyle = "rgba(0, 255, 163, 0.25)";
        ctx.lineWidth = 0.8;
        ctx.shadowBlur = 0;
        ctx.stroke();

        ctx.restore();
      }
      animId = requestAnimationFrame(render);
    };

    animId = requestAnimationFrame(render);

    return () => {
      cancelAnimationFrame(animId);
      observer.disconnect();
      document.removeEventListener("visibilitychange", handleVis);
    };
  }, []);

  return <canvas ref={canvasRef} className="panel-corner-waves" />;
}

export function PlayerCenterWaves({ playing = false }: { playing?: boolean }) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animId: number;
    let isVisible = true;
    const handleVis = () => {
      isVisible = !document.hidden;
    };
    document.addEventListener("visibilitychange", handleVis);

    let width = 0;
    let height = 0;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);

    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      width = rect.width;
      height = rect.height;
      canvas.width = Math.floor(width * dpr);
      canvas.height = Math.floor(height * dpr);
    };
    resize();

    const observer = new ResizeObserver(resize);
    observer.observe(canvas);

    const render = (time: number) => {
      if (isVisible && width > 0 && height > 0) {
        ctx.save();
        ctx.scale(dpr, dpr);
        ctx.clearRect(0, 0, width, height);

        const speedMul = playing ? 2.1 : 1.15;
        const ampMul = playing ? 1.4 : 0.95;
        const t = time * 0.001 * speedMul;
        const centerX = width / 2;
        const baseline = height * 0.58;

        const points: { x: number; y1: number; y2: number; y3: number; fade: number }[] = [];
        const step = 3;

        for (let x = 0; x <= width; x += step) {
          const distFromCenter = Math.abs(x - centerX);
          let centerFade = 1.0;
          if (distFromCenter < 46) {
            centerFade = 0.22 + 0.78 * Math.pow(distFromCenter / 46, 1.4);
          }

          const edgeDist = Math.min(x, width - x);
          const edgeFade = edgeDist < 32 ? edgeDist / 32 : 1.0;
          const totalFade = centerFade * edgeFade;

          const phase = x * 0.032 - t * 2.6;
          const y1 =
            baseline +
            Math.sin(phase) * (7.5 * ampMul) +
            Math.cos(phase * 1.6 + t * 1.2) * (4 * ampMul);

          const y2 =
            baseline +
            5 +
            Math.sin(phase * 0.85 - t * 1.5 + 1.2) * (5.5 * ampMul) +
            Math.cos(phase * 1.8 + t * 0.9) * (2.8 * ampMul);

          const y3 =
            baseline +
            10 +
            Math.sin(phase * 0.7 + t * 1.1 + 2.4) * (4 * ampMul);

          points.push({ x, y1, y2, y3, fade: totalFade });
        }

        ctx.beginPath();
        ctx.moveTo(0, height);
        points.forEach((p) => ctx.lineTo(p.x, p.y1));
        ctx.lineTo(width, height);
        ctx.closePath();

        const fillGrad = ctx.createLinearGradient(0, baseline - 15, 0, height);
        fillGrad.addColorStop(0, "rgba(0, 255, 163, 0.16)");
        fillGrad.addColorStop(1, "rgba(0, 255, 163, 0.0)");
        ctx.fillStyle = fillGrad;
        ctx.fill();

        for (let i = 0; i < points.length - 1; i++) {
          const p1 = points[i];
          const p2 = points[i + 1];
          const avgFade = (p1.fade + p2.fade) / 2;

          ctx.beginPath();
          ctx.moveTo(p1.x, p1.y1);
          ctx.lineTo(p2.x, p2.y1);

          ctx.strokeStyle = `rgba(0, 255, 163, ${0.9 * avgFade})`;
          ctx.lineWidth = 2.2;
          ctx.shadowColor = "#00FFA3";
          ctx.shadowBlur = 10 * avgFade;
          ctx.stroke();
        }

        for (let i = 0; i < points.length - 1; i++) {
          const p1 = points[i];
          const p2 = points[i + 1];
          const avgFade = (p1.fade + p2.fade) / 2;

          ctx.beginPath();
          ctx.moveTo(p1.x, p1.y2);
          ctx.lineTo(p2.x, p2.y2);

          ctx.strokeStyle = `rgba(0, 255, 163, ${0.45 * avgFade})`;
          ctx.lineWidth = 1.3;
          ctx.shadowBlur = 4 * avgFade;
          ctx.stroke();
        }

        for (let i = 0; i < points.length - 1; i += 2) {
          const p1 = points[i];
          const p2 = points[Math.min(i + 2, points.length - 1)];
          const avgFade = (p1.fade + p2.fade) / 2;

          ctx.beginPath();
          ctx.moveTo(p1.x, p1.y3);
          ctx.lineTo(p2.x, p2.y3);

          ctx.strokeStyle = `rgba(0, 255, 163, ${0.25 * avgFade})`;
          ctx.lineWidth = 0.9;
          ctx.shadowBlur = 0;
          ctx.stroke();
        }

        ctx.restore();
      }
      animId = requestAnimationFrame(render);
    };

    animId = requestAnimationFrame(render);

    return () => {
      cancelAnimationFrame(animId);
      observer.disconnect();
      document.removeEventListener("visibilitychange", handleVis);
    };
  }, [playing]);

  return <canvas ref={canvasRef} className="player-continuous-wave" />;
}
