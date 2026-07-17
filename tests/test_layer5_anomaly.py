"""Layer 5 tests: train a small autoencoder and check anomaly behaviour."""

import numpy as np
import torch
import pytest

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import ANOMALY, ANOMALY_FEATURES
from src.layer5_anomaly import (SessionAutoencoder, SessionAnomalyDetector,
                                simulate_sessions)


@pytest.fixture(scope="module")
def checkpoint(tmp_path_factory):
    # quick training run, same code path as scripts/train_anomaly.py
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
        "error_mean": float(errors.mean()), "error_std": float(errors.std()),
    }, path)
    return str(path)


def normal_session():
    # a typical good session, in ANOMALY_FEATURES order
    return np.array([6.0, 4.0, -2.0, 0.8, 0.8, 15.0, 0.85, 0.2, 0.02, 10, 14.0, 2.0])


def crazy_session():
    # everything out of distribution at once
    return np.array([0.1, 10.0, 9.9, 0.01, 0.01, 300.0, 0.0, 5.0, 0.9, 500, 3.0, 200.0])


def test_normal_session_passes(checkpoint):
    det = SessionAnomalyDetector(checkpoint)
    r = det.check("user1", normal_session())
    assert not r["anomaly"]
    assert r["severity"] == "none"


def test_extreme_session_flags(checkpoint):
    det = SessionAnomalyDetector(checkpoint)
    r = det.check("user1", crazy_session())
    assert r["anomaly"]
    assert r["severity"] in ("mild", "moderate", "severe")
    assert len(r["reasons"]) >= 1


def test_threshold_personalises(checkpoint):
    det = SessionAnomalyDetector(checkpoint)
    for _ in range(det.MIN_PERSONAL_SESSIONS):
        det.check("user2", normal_session())
    r = det.check("user2", normal_session())
    assert r["personalised"]


def test_feature_count_guard(checkpoint):
    det = SessionAnomalyDetector(checkpoint)
    with pytest.raises(AssertionError):
        det.check("user3", np.zeros(5))
