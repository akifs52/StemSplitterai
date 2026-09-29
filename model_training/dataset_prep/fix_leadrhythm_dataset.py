"""Create a cleaned lead/rhythm dataset from prepared stem folders.

The original Slakh build can contain full-song mixtures while the targets contain
only guitar stems. This script rewrites each sample so:

    mixture = lead_guitar + rhythm_guitar

It can also skip tracks where either target stem is effectively silent.
"""

import argparse
import os
from pathlib import Path

import numpy as np
import soundfile as sf
from tqdm import tqdm


def first_existing(folder: Path, stem: str) -> Path | None:
    for ext in ("flac", "wav"):
        path = folder / f"{stem}.{ext}"
        if path.exists():
            return path
    return None


def read_audio(path: Path) -> tuple[np.ndarray, int]:
    data, sr = sf.read(path, always_2d=True, dtype="float32")
    return data, sr


def rms(audio: np.ndarray) -> float:
    if audio.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(audio * audio)))


def fix_split(src_root: Path, dst_root: Path, min_rms: float,
              swap_labels: bool) -> dict[str, int]:
    stats = {
        "seen": 0,
        "written": 0,
        "missing": 0,
        "sr_mismatch": 0,
        "silent": 0,
        "length_mismatch": 0,
    }
    dst_root.mkdir(parents=True, exist_ok=True)

    track_dirs = sorted(path for path in src_root.iterdir() if path.is_dir())
    for src_dir in tqdm(track_dirs, desc=f"Fixing {src_root.name}"):
        stats["seen"] += 1
        lead_path = first_existing(src_dir, "lead_guitar")
        rhythm_path = first_existing(src_dir, "rhythm_guitar")
        if lead_path is None or rhythm_path is None:
            stats["missing"] += 1
            continue

        lead, lead_sr = read_audio(lead_path)
        rhythm, rhythm_sr = read_audio(rhythm_path)
        if lead_sr != rhythm_sr:
            stats["sr_mismatch"] += 1
            continue

        n = min(len(lead), len(rhythm))
        if n != len(lead) or n != len(rhythm):
            stats["length_mismatch"] += 1
        lead = lead[:n]
        rhythm = rhythm[:n]

        if rms(lead) < min_rms or rms(rhythm) < min_rms:
            stats["silent"] += 1
            continue

        if swap_labels:
            lead, rhythm = rhythm, lead

        dst_dir = dst_root / src_dir.name
        dst_dir.mkdir(parents=True, exist_ok=True)
        mixture = lead + rhythm

        sf.write(dst_dir / "mixture.flac", mixture, lead_sr)
        sf.write(dst_dir / "lead_guitar.flac", lead, lead_sr)
        sf.write(dst_dir / "rhythm_guitar.flac", rhythm, lead_sr)
        stats["written"] += 1

    return stats


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train_in", default="D:/qt/stemsplitteraiapp/dataset/train_slakh")
    parser.add_argument("--valid_in", default="D:/qt/stemsplitteraiapp/dataset/valid_slakh")
    parser.add_argument("--train_out", default="D:/qt/stemsplitteraiapp/dataset/train_slakh_fixed")
    parser.add_argument("--valid_out", default="D:/qt/stemsplitteraiapp/dataset/valid_slakh_fixed")
    parser.add_argument("--min_rms", type=float, default=1e-4)
    parser.add_argument("--swap_labels", action="store_true",
                        help="Write rhythm input stems as lead_guitar and lead input stems as rhythm_guitar.")
    args = parser.parse_args()

    for src, dst in (
        (Path(args.train_in), Path(args.train_out)),
        (Path(args.valid_in), Path(args.valid_out)),
    ):
        if not src.exists():
            raise FileNotFoundError(src)
        stats = fix_split(src, dst, args.min_rms, args.swap_labels)
        print(f"\n{src.name} -> {dst.name}")
        for key, value in stats.items():
            print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
