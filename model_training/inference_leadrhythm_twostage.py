"""Two-stage lead/rhythm guitar separation runner.

Stage 1 extracts a guitar stem with Demucs. Stage 2 splits that guitar stem
with the trained lead/rhythm model.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


AUDIO_EXTS = {".wav", ".flac", ".mp3", ".m4a", ".ogg", ".aac"}


def resolve_path(value: str, fallback_base: Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    if path.exists():
        return path.resolve()
    return (fallback_base / path).resolve()


def collect_audio(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if not path.is_dir():
        raise FileNotFoundError(path)
    return sorted(p for p in path.rglob("*") if p.is_file() and p.suffix.lower() in AUDIO_EXTS)


def run_demucs(files: list[Path], args: argparse.Namespace, stage1_dir: Path) -> list[Path]:
    guitar_paths: list[Path] = []
    for audio_path in files:
        cmd = [
            sys.executable,
            "-m",
            "demucs",
            "-n",
            args.demucs_model,
            "-o",
            str(stage1_dir),
            "--shifts",
            str(args.demucs_shifts),
            "--overlap",
            str(args.demucs_overlap),
        ]
        if args.demucs_segment > 0:
            cmd += ["--segment", str(args.demucs_segment)]
        if args.device:
            cmd += ["--device", args.device]
        cmd.append(str(audio_path))

        print("Stage 1:", " ".join(cmd))
        subprocess.run(cmd, check=True)

        expected = stage1_dir / args.demucs_model / audio_path.stem / "guitar.wav"
        if not expected.exists():
            raise FileNotFoundError(f"Demucs guitar stem not found: {expected}")
        guitar_paths.append(expected)
    return guitar_paths


def prepare_stage2_input(guitar_paths: list[Path], stage2_input: Path) -> None:
    stage2_input.mkdir(parents=True, exist_ok=True)
    used_names: set[str] = set()

    for idx, guitar_path in enumerate(guitar_paths, start=1):
        song_name = guitar_path.parent.name
        if song_name in used_names:
            song_name = f"{song_name}_{idx:03d}"
        used_names.add(song_name)

        song_dir = stage2_input / song_name
        song_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(guitar_path, song_dir / "guitar.wav")


def run_stage2(args: argparse.Namespace, stage2_input: Path, stage2_output: Path) -> None:
    script_dir = Path(__file__).resolve().parent
    cmd = [
        sys.executable,
        str(script_dir / "inference.py"),
        "--model_type",
        args.model_type,
        "--config_path",
        args.config_path,
        "--start_check_point",
        args.checkpoint,
        "--input_folder",
        str(stage2_input),
        "--store_dir",
        str(stage2_output),
        "--filename_template",
        "{dir_name}/{instr}",
        "--bigshifts",
        str(args.bigshifts),
        "--pcm_type",
        args.pcm_type,
    ]
    if args.use_tta:
        cmd.append("--use_tta")
    if args.force_cpu:
        cmd.append("--force_cpu")
    if args.device_id is not None:
        cmd += ["--device_ids", str(args.device_id)]

    print("Stage 2:", " ".join(cmd))
    subprocess.run(cmd, check=True)


def swap_outputs(stage2_output: Path) -> None:
    for song_dir in sorted(p for p in stage2_output.iterdir() if p.is_dir()):
        lead = song_dir / "lead_guitar.wav"
        rhythm = song_dir / "rhythm_guitar.wav"
        if not lead.exists() or not rhythm.exists():
            lead = song_dir / "lead_guitar.flac"
            rhythm = song_dir / "rhythm_guitar.flac"
        if not lead.exists() or not rhythm.exists():
            continue

        tmp = song_dir / "_swap_tmp_audio"
        lead.rename(tmp)
        rhythm.rename(lead)
        tmp.rename(rhythm)
        print(f"Swapped labels: {song_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Two-stage lead/rhythm guitar separation")
    parser.add_argument("--input", required=True, help="Full song, guitar.wav, or folder")
    parser.add_argument("--output", required=True, help="Output folder")
    parser.add_argument("--checkpoint", required=True, help="Lead/rhythm model checkpoint")
    parser.add_argument("--config_path", default="configs/config_leadrhythm_v2.yaml")
    parser.add_argument("--model_type", default="mel_band_roformer")
    parser.add_argument("--skip_stage1", action="store_true",
                        help="Input is already guitar stems; skip Demucs extraction.")
    parser.add_argument("--swap_outputs", action="store_true",
                        help="Swap lead_guitar and rhythm_guitar output files.")
    parser.add_argument("--use_tta", action="store_true")
    parser.add_argument("--bigshifts", type=int, default=2)
    parser.add_argument("--pcm_type", default="FLOAT", choices=["PCM_16", "PCM_24", "FLOAT"])
    parser.add_argument("--force_cpu", action="store_true")
    parser.add_argument("--device_id", type=int, default=0)
    parser.add_argument("--device", default="", help="Demucs device: cuda or cpu. Empty means Demucs default.")
    parser.add_argument("--demucs_model", default="htdemucs_6s")
    parser.add_argument("--demucs_shifts", type=int, default=2)
    parser.add_argument("--demucs_overlap", type=float, default=0.25)
    parser.add_argument("--demucs_segment", type=float, default=7.8)
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    args.config_path = str(resolve_path(args.config_path, script_dir))
    args.checkpoint = str(resolve_path(args.checkpoint, Path.cwd()))

    input_path = Path(args.input).resolve()
    output_dir = Path(args.output).resolve()
    stage1_dir = output_dir / "_stage1_demucs"
    stage2_input = output_dir / "_stage2_input"
    stage2_output = output_dir / "lead_rhythm"

    files = collect_audio(input_path)
    if not files:
        raise RuntimeError(f"No audio files found in {input_path}")

    if args.skip_stage1:
        guitar_paths = files
    else:
        guitar_paths = run_demucs(files, args, stage1_dir)

    prepare_stage2_input(guitar_paths, stage2_input)
    run_stage2(args, stage2_input, stage2_output)

    if args.swap_outputs:
        swap_outputs(stage2_output)

    print(f"Done. Results: {stage2_output}")


if __name__ == "__main__":
    main()
