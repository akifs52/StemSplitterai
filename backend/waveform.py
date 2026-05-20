import numpy as np


def compute_waveform(file_path, max_points=800):
    try:
        import librosa
        y, sr = librosa.load(file_path, sr=None, mono=True)
        if len(y) == 0:
            return []
        block_size = max(1, len(y) // max_points)
        envelope = []
        for i in range(0, len(y), block_size):
            block = y[i : i + block_size]
            envelope.append(float(np.max(np.abs(block))))
        if len(envelope) < max_points:
            envelope += [0.0] * (max_points - len(envelope))
        return envelope[:max_points]
    except ImportError:
        return []
    except Exception:
        return []
