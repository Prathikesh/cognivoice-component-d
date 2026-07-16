"""Layer 1: ambient noise and audio quality gate.

Pure DSP, no ML. Rejects clips that are too quiet, too loud, clipped,
pure noise, or too short, so Layer 2 only ever scores usable speech.
"""

import numpy as np

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import AMBIENT, MIN_DURATION_SEC, SAMPLE_RATE


def _rms(audio: np.ndarray) -> float:
    return float(np.sqrt(np.mean(audio ** 2)))


def _clip_ratio(audio: np.ndarray) -> float:
    # fraction of samples sitting at or near the digital ceiling
    return float(np.mean(np.abs(audio) > 0.99))


def _spectral_flatness(audio: np.ndarray, n_fft: int = 1024) -> float:
    # flatness near 1 = white-noise-like, near 0 = tonal/speech-like
    spec = np.abs(np.fft.rfft(audio[: min(len(audio), SAMPLE_RATE * 5)], n=n_fft)) + 1e-10
    geometric = np.exp(np.mean(np.log(spec)))
    arithmetic = np.mean(spec)
    return float(geometric / arithmetic)


def _estimate_snr_db(audio: np.ndarray, frame_len: int = 400) -> float:
    # frame-level energy: loudest frames ~ speech, quietest frames ~ noise floor
    n_frames = len(audio) // frame_len
    if n_frames < 4:
        return 0.0
    frames = audio[: n_frames * frame_len].reshape(n_frames, frame_len)
    energies = np.sqrt(np.mean(frames ** 2, axis=1))
    energies = np.sort(energies)
    noise = np.mean(energies[: max(1, n_frames // 10)]) + 1e-10
    speech = np.mean(energies[-max(1, n_frames // 10):]) + 1e-10
    return float(20 * np.log10(speech / noise))


def check_ambient(audio: np.ndarray, sr: int = SAMPLE_RATE) -> dict:
    """Run all quality checks. Returns ok flag, reasons, and raw metrics."""
    audio = np.asarray(audio, dtype=np.float32).flatten()
    reasons = []

    duration = len(audio) / sr
    if duration < MIN_DURATION_SEC:
        reasons.append(f"too_short: {duration:.2f}s < {MIN_DURATION_SEC}s")

    rms = _rms(audio)
    if rms < AMBIENT["min_rms"]:
        reasons.append(f"too_quiet: rms {rms:.4f} < {AMBIENT['min_rms']}")
    if rms > AMBIENT["max_rms"]:
        reasons.append(f"too_loud: rms {rms:.4f} > {AMBIENT['max_rms']}")

    clip = _clip_ratio(audio)
    if clip > AMBIENT["max_clip_ratio"]:
        reasons.append(f"clipping: {clip:.3f} > {AMBIENT['max_clip_ratio']}")

    flatness = _spectral_flatness(audio)
    if flatness > AMBIENT["max_flatness"]:
        reasons.append(f"noise_like: flatness {flatness:.3f} > {AMBIENT['max_flatness']}")

    snr = _estimate_snr_db(audio)
    # skip the SNR check for clips already rejected as silent
    if rms >= AMBIENT["min_rms"] and snr < AMBIENT["min_snr_db"]:
        reasons.append(f"low_snr: {snr:.1f}dB < {AMBIENT['min_snr_db']}dB")

    return {
        "ok": len(reasons) == 0,
        "reasons": reasons,
        "metrics": {
            "duration_sec": round(duration, 2),
            "rms": round(rms, 5),
            "clip_ratio": round(clip, 4),
            "spectral_flatness": round(flatness, 4),
            "snr_db": round(snr, 1),
        },
    }
