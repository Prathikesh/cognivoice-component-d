"""API smoke tests with FastAPI's TestClient.

Checkpoints are absent in CI, so /infer and /anomaly-check must return
clean 503s while every rule-based endpoint works end to end.
"""

import io
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))
import api_server
from config import SAMPLE_RATE

client = TestClient(api_server.app)


def wav_bytes(audio: np.ndarray) -> bytes:
    buf = io.BytesIO()
    sf.write(buf, audio, SAMPLE_RATE, format="WAV")
    return buf.getvalue()


def speech_like(seconds: float = 3.0) -> np.ndarray:
    t = np.linspace(0, seconds, int(SAMPLE_RATE * seconds))
    carrier = 0.3 * np.sin(2 * np.pi * 150 * t) + 0.1 * np.sin(2 * np.pi * 450 * t)
    envelope = (np.sin(2 * np.pi * 3 * t) > 0).astype(float)
    return (carrier * envelope).astype(np.float32)


def seed_session(sid: str, pre: float, post: float):
    """Place Layer 2 results directly, as /infer would after training."""
    api_server.session_scores[sid] = {
        "pre": {"stress_score": pre, "confidence": 0.8, "arousal": 0.5,
                "quality": {"rms": 0.02}},
        "post": {"stress_score": post, "confidence": 0.8, "arousal": 0.1,
                 "quality": {"rms": 0.02}},
    }


def test_health_reports_layer_status():
    r = client.get("/health")
    assert r.status_code == 200
    layers = r.json()["layers"]
    assert layers["layer1_quality"] and layers["layer3_compare"]


def test_ambient_check_accepts_clean_audio():
    r = client.post("/ambient-check",
                    files={"file": ("a.wav", wav_bytes(speech_like()),
                                    "audio/wav")})
    assert r.status_code == 200 and r.json()["ok"]


def test_ambient_check_rejects_silence():
    silence = np.zeros(SAMPLE_RATE * 3, dtype=np.float32)
    r = client.post("/ambient-check",
                    files={"file": ("s.wav", wav_bytes(silence), "audio/wav")})
    assert r.status_code == 200 and not r.json()["ok"]


def test_infer_503_without_checkpoint():
    r = client.post("/infer",
                    files={"file": ("a.wav", wav_bytes(speech_like()),
                                    "audio/wav")})
    assert r.status_code == 503


def test_compare_flow():
    seed_session("s-compare", pre=7.0, post=3.0)
    r = client.post("/compare", json={"session_id": "s-compare"})
    assert r.status_code == 200 and r.json()["improved"]


def test_compare_unknown_session_404():
    r = client.post("/compare", json={"session_id": "nope"})
    assert r.status_code == 404


def test_hrv_push_then_cross_validate():
    seed_session("s-hrv", pre=7.0, post=3.0)
    for phase, rmssd in [("pre", 30.0), ("post", 65.0)]:
        r = client.post("/session-update", json={
            "session_id": "s-hrv", "phase": phase, "rmssd": rmssd})
        assert r.status_code == 200
    r = client.post("/cross-validate", json={"session_id": "s-hrv"})
    assert r.status_code == 200 and r.json()["validated"]


def test_cross_validate_mock_fallback():
    seed_session("s-mock", pre=7.0, post=3.0)
    r = client.post("/cross-validate",
                    json={"session_id": "s-mock", "use_mock_hrv": True})
    assert r.status_code == 200


def test_cross_validate_without_hrv_404():
    seed_session("s-nohrv", pre=7.0, post=3.0)
    r = client.post("/cross-validate", json={"session_id": "s-nohrv"})
    assert r.status_code == 404


def test_full_session_payload():
    seed_session("s-full", pre=7.0, post=3.0)
    r = client.post("/full-session", json={
        "session_id": "s-full", "user_id": "u1", "use_mock_hrv": True})
    assert r.status_code == 200
    body = r.json()
    assert body["stress_level"] == 3.0
    assert body["comparison"]["improved"]
    assert body["crossmodal"] is not None
    # anomaly model not loaded in CI -> that section is None, not a crash
    assert body["anomaly"] is None


def test_anomaly_503_without_checkpoint():
    r = client.post("/anomaly-check",
                    json={"user_id": "u1", "features": [0.0] * 12})
    assert r.status_code == 503
