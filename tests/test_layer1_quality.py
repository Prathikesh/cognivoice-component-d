"""Layer 1 tests: synthetic audio with known properties must pass/fail
the quality gate exactly as designed."""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import SAMPLE_RATE
from src.layer1_quality import check_quality


def speech_like(seconds: float = 3.0) -> np.ndarray:
    """Amplitude-modulated tones: tonal like speech, with pauses."""
    t = np.linspace(0, seconds, int(SAMPLE_RATE * seconds))
    carrier = 0.3 * np.sin(2 * np.pi * 150 * t) + 0.1 * np.sin(2 * np.pi * 450 * t)
    envelope = (np.sin(2 * np.pi * 3 * t) > 0).astype(float)
    return (carrier * envelope).astype(np.float32)


def test_clean_speech_passes():
    result = check_quality(speech_like())
    assert result["ok"], result["reasons"]


def test_silence_fails():
    result = check_quality(np.zeros(SAMPLE_RATE * 3, dtype=np.float32))
    assert not result["ok"]
    assert any("too_quiet" in r for r in result["reasons"])


def test_too_short_fails():
    result = check_quality(speech_like(0.3))
    assert not result["ok"]
    assert any("too_short" in r for r in result["reasons"])


def test_clipped_audio_fails():
    clipped = np.clip(speech_like() * 10, -1.0, 1.0)
    result = check_quality(clipped)
    assert not result["ok"]
    assert any("clipping" in r for r in result["reasons"])


def test_pure_noise_fails():
    rng = np.random.RandomState(0)
    noise = (0.1 * rng.randn(SAMPLE_RATE * 3)).astype(np.float32)
    result = check_quality(noise)
    assert not result["ok"]
    assert any("noise_like" in r or "low_snr" in r for r in result["reasons"])


def test_metrics_always_reported():
    result = check_quality(speech_like())
    for key in ["duration_sec", "rms", "clip_ratio", "spectral_flatness", "snr_db"]:
        assert key in result["metrics"]
