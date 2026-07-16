"""Layer 2a: prosodic feature extraction.

These features (pitch, jitter, shimmer, HNR, energy, rate, pauses) are
physiological stress markers and largely language-independent. They form
the second input branch of the fusion model.
"""

import numpy as np
import librosa
import parselmouth

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import SAMPLE_RATE

# fixed feature order; the model reads its input size from this list
FEATURE_NAMES = [
    "f0_mean", "f0_std", "f0_min", "f0_max", "f0_range", "f0_median",
    "jitter_local", "shimmer_local", "hnr_mean",
    "rms_mean", "rms_std", "rms_max",
    "zcr_mean",
    "centroid_mean", "centroid_std", "rolloff_mean", "flatness_mean",
    "speech_rate", "pause_ratio", "voiced_fraction",
    "duration_sec",
]
N_FEATURES = len(FEATURE_NAMES)


def _pitch_features(sound: parselmouth.Sound) -> dict:
    # F0 statistics from voiced frames only
    pitch = sound.to_pitch(pitch_floor=60.0, pitch_ceiling=500.0)
    f0 = pitch.selected_array["frequency"]
    voiced = f0[f0 > 0]
    if len(voiced) < 2:
        return {k: 0.0 for k in ["f0_mean", "f0_std", "f0_min", "f0_max",
                                 "f0_range", "f0_median", "voiced_fraction"]}
    return {
        "f0_mean": float(np.mean(voiced)),
        "f0_std": float(np.std(voiced)),
        "f0_min": float(np.min(voiced)),
        "f0_max": float(np.max(voiced)),
        "f0_range": float(np.max(voiced) - np.min(voiced)),
        "f0_median": float(np.median(voiced)),
        "voiced_fraction": float(len(voiced) / len(f0)),
    }


def _voice_quality(sound: parselmouth.Sound) -> dict:
    # jitter and shimmer measure cycle-to-cycle instability of the voice,
    # both rise under stress; HNR drops when the voice gets rougher
    out = {"jitter_local": 0.0, "shimmer_local": 0.0, "hnr_mean": 0.0}
    try:
        pp = parselmouth.praat.call(sound, "To PointProcess (periodic, cc)", 60, 500)
        out["jitter_local"] = float(parselmouth.praat.call(
            pp, "Get jitter (local)", 0, 0, 0.0001, 0.02, 1.3))
        out["shimmer_local"] = float(parselmouth.praat.call(
            [sound, pp], "Get shimmer (local)", 0, 0, 0.0001, 0.02, 1.3, 1.6))
        harm = parselmouth.praat.call(sound, "To Harmonicity (cc)", 0.01, 60, 0.1, 1.0)
        out["hnr_mean"] = float(parselmouth.praat.call(harm, "Get mean", 0, 0))
    except Exception:
        pass  # unvoiced or too-short audio: keep zeros
    for k, v in out.items():
        if not np.isfinite(v):
            out[k] = 0.0
    return out


def _energy_spectral(audio: np.ndarray, sr: int) -> dict:
    rms = librosa.feature.rms(y=audio)[0]
    zcr = librosa.feature.zero_crossing_rate(y=audio)[0]
    centroid = librosa.feature.spectral_centroid(y=audio, sr=sr)[0]
    rolloff = librosa.feature.spectral_rolloff(y=audio, sr=sr)[0]
    flatness = librosa.feature.spectral_flatness(y=audio)[0]

    # frames quieter than 10% of the loudest frame count as pauses
    pause_ratio = float(np.mean(rms < 0.1 * (np.max(rms) + 1e-10)))

    # onset rate approximates syllable/speech rate per second
    onsets = librosa.onset.onset_detect(y=audio, sr=sr)
    speech_rate = float(len(onsets) / (len(audio) / sr))

    return {
        "rms_mean": float(np.mean(rms)),
        "rms_std": float(np.std(rms)),
        "rms_max": float(np.max(rms)),
        "zcr_mean": float(np.mean(zcr)),
        "centroid_mean": float(np.mean(centroid)),
        "centroid_std": float(np.std(centroid)),
        "rolloff_mean": float(np.mean(rolloff)),
        "flatness_mean": float(np.mean(flatness)),
        "speech_rate": speech_rate,
        "pause_ratio": pause_ratio,
    }


def extract_prosody(audio: np.ndarray, sr: int = SAMPLE_RATE) -> np.ndarray:
    """Return the feature vector in FEATURE_NAMES order for one audio clip."""
    audio = np.asarray(audio, dtype=np.float64).flatten()
    sound = parselmouth.Sound(audio, sampling_frequency=sr)

    feats = {}
    feats.update(_pitch_features(sound))
    feats.update(_voice_quality(sound))
    feats.update(_energy_spectral(audio.astype(np.float32), sr))
    feats["duration_sec"] = float(len(audio) / sr)

    vec = np.array([feats[name] for name in FEATURE_NAMES], dtype=np.float32)
    # never let a NaN/inf reach the model
    return np.nan_to_num(vec, nan=0.0, posinf=0.0, neginf=0.0)


def extract_prosody_file(path: str) -> np.ndarray:
    """Load an audio file (any format/rate) and extract prosody features."""
    audio, _ = librosa.load(path, sr=SAMPLE_RATE, mono=True)
    return extract_prosody(audio, SAMPLE_RATE)
