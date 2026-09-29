import { useEffect, useRef } from "react";
import { drawWave } from "../waveform";

export interface WaveCanvasProps {
  data: number[];
  color: string;
  position?: number;
  mode?: "center" | "bottom";
  showProgress?: boolean;
  className?: string;
  height?: number;
}

export function WaveCanvas({
  data,
  color,
  position = 0,
  mode = "center",
  showProgress = true,
  className = "",
  height = 150
}: WaveCanvasProps) {
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
