"""Layer 5 tests: train a small autoencoder in-test, then verify that
normal sessions pass, extreme sessions flag, and thresholds personalise."""

import sys
from pathlib import Path

import numpy as np
import pytest
import torch

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import ANOMALY, ANOMALY_FEATURES
from src.layer5_anomaly import (SessionAnomalyDetector, SessionAutoencoder,
                                simulate_sessions)


@pytest.fixture(scope="module")
def checkpoint(tmp_path_factory):
    """Quick training run - same recipe as scripts/train_anomaly.py."""
    data = simulate_sessions(1000)
    mean, std = data.mean(axis=0), data.std(axis=0) + 1e-8
    x = torch.from_numpy((data - mean) / std)

    torch.manual_seed(0)
    model = SessionAutoencoder(len(ANOMALY_FEATURES), ANOMALY["hidden_dims"])
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    for _ in range(300):
        opt.zero_grad()
        loss = ((model(x) - x) ** 2).mean()
        loss.backward()
        opt.step()

    model.eval()
    with torch.no_grad():
        errors = ((model(x) - x) ** 2).mean(dim=1).numpy()
    path = tmp_path_factory.mktemp("models") / "anomaly_test.pt"
    torch.save({
        "state_dict": model.state_dict(),
        "n_features": len(ANOMALY_FEATURES),
        "hidden_dims": ANOMALY["hidden_dims"],
        "feat_mean": mean, "feat_std": std,
        "threshold": float(errors.mean() + 3 * errors.std()),
    }, path)
    return str(path)


def normal_session():
    return np.array([6.0, 4.0, -2.0, 0.8, 0.8, 15.0, 0.85, 0.2, 0.02,
                     10, 14.0, 2.0])


def extreme_session():
    return np.array([0.1, 10.0, 9.9, 0.01, 0.01, 300.0, 0.0, 5.0, 0.9,
                     500, 3.0, 200.0])


def test_normal_session_passes(checkpoint):
    det = SessionAnomalyDetector(checkpoint)
    r = det.check("user1", normal_session())
    assert not r["anomaly"] and r["severity"] == "none"


def test_extreme_session_flags(checkpoint):
    det = SessionAnomalyDetector(checkpoint)
    r = det.check("user1", extreme_session())
    assert r["anomaly"]
    assert r["severity"] in ("mild", "moderate", "severe")
    assert len(r["reasons"]) >= 1   # explainability: reasons must be named


def test_threshold_personalises_after_history(checkpoint):
    det = SessionAnomalyDetector(checkpoint)
    for _ in range(ANOMALY["min_personal_sessions"]):
        det.check("user2", normal_session())
    r = det.check("user2", normal_session())
    assert r["personalised"]


def test_wrong_feature_count_rejected(checkpoint):
    det = SessionAnomalyDetector(checkpoint)
    with pytest.raises(AssertionError):
        det.check("user3", np.zeros(5))
