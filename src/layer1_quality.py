"""Layer 1: audio quality gate.

Pure signal processing, no ML. Every recording passes through here
before Layer 2; garbage audio (silence, noise, distortion) is rejected
with human-readable reasons so the app can ask the user to re-record.
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import QUALITY, MIN_DURATION_SEC, SAMPLE_RATE


def _rms(audio: np.ndarray) -> float:
    """Root-mean-square energy: the overall loudness of the clip."""
    return float(np.sqrt(np.mean(audio ** 2)))


def _clip_ratio(audio: np.ndarray) -> float:
    """Fraction of samples at the digital ceiling (|x| > 0.99).
    High values mean the microphone was overloaded and the waveform
    is distorted - unusable for voice analysis."""
    return float(np.mean(np.abs(audio) > 0.99))


def _spectral_flatness(audio: np.ndarray, n_fft: int = 1024) -> float:
    """Geometric mean / arithmetic mean of the spectrum.
    Near 1.0 = flat spectrum = white-noise-like (fan, hiss).
    Near 0.0 = peaky spectrum = tonal content like speech."""
    segment = audio[: min(len(audio), SAMPLE_RATE * 5)]
    spectrum = np.abs(np.fft.rfft(segment, n=n_fft)) + 1e-10
    geometric = np.exp(np.mean(np.log(spectrum)))
    arithmetic = np.mean(spectrum)
    return float(geometric / arithmetic)


def _estimate_snr_db(audio: np.ndarray, frame_len: int = 400) -> float:
    """Speech-to-noise ratio estimate without a separate noise recording.
    Trick: split into 25 ms frames; the quietest 10% of frames approximate
    the noise floor, the loudest 10% approximate speech."""
    n_frames = len(audio) // frame_len
    if n_frames < 4:
        return 0.0
    frames = audio[: n_frames * frame_len].reshape(n_frames, frame_len)
    energies = np.sort(np.sqrt(np.mean(frames ** 2, axis=1)))
    tenth = max(1, n_frames // 10)
    noise = np.mean(energies[:tenth]) + 1e-10
    speech = np.mean(energies[-tenth:]) + 1e-10
    return float(20 * np.log10(speech / noise))


def check_quality(audio: np.ndarray, sr: int = SAMPLE_RATE) -> dict:
    """Run every quality check on one clip.

    Returns {ok, reasons, metrics}. `ok` is True only when ALL checks
    pass; `reasons` lists every failure so the app can explain exactly
    what was wrong with the recording.
    """
    audio = np.asarray(audio, dtype=np.float32).flatten()
    reasons = []

    duration = len(audio) / sr
    if duration < MIN_DURATION_SEC:
        reasons.append(f"too_short: {duration:.2f}s < {MIN_DURATION_SEC}s")

    rms = _rms(audio)
    if rms < QUALITY["min_rms"]:
        reasons.append(f"too_quiet: rms {rms:.4f}")
    if rms > QUALITY["max_rms"]:
        reasons.append(f"too_loud: rms {rms:.4f}")

    clip = _clip_ratio(audio)
    if clip > QUALITY["max_clip_ratio"]:
        reasons.append(f"clipping: {clip:.3f} of samples at ceiling")

    flatness = _spectral_flatness(audio)
    if flatness > QUALITY["max_flatness"]:
        reasons.append(f"noise_like: flatness {flatness:.3f}")

    snr = _estimate_snr_db(audio)
    # SNR only meaningful when there is actually signal present
    if rms >= QUALITY["min_rms"] and snr < QUALITY["min_snr_db"]:
        reasons.append(f"low_snr: {snr:.1f} dB")

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
