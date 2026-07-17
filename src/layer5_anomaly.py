"""Layer 5: longitudinal anomaly detection over session summaries.

An autoencoder learns what normal sessions look like; a session whose
reconstruction error is far above the user's own baseline is flagged,
with severity and the features that drove it.
"""

import numpy as np
import torch
import torch.nn as nn

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import ANOMALY, ANOMALY_FEATURES

N_FEATURES = len(ANOMALY_FEATURES)


class SessionAutoencoder(nn.Module):
    """12 -> 16 -> 8 -> 4 -> 8 -> 16 -> 12, per config."""

    def __init__(self, n_features: int = N_FEATURES,
                 hidden_dims: list[int] | None = None):
        super().__init__()
        dims = hidden_dims or ANOMALY["hidden_dims"]

        enc, last = [], n_features
        for d in dims:
            enc += [nn.Linear(last, d), nn.ReLU()]
            last = d
        self.encoder = nn.Sequential(*enc[:-1])  # no ReLU on the bottleneck

        dec, last = [], dims[-1]
        for d in reversed(dims[:-1]):
            dec += [nn.Linear(last, d), nn.ReLU()]
            last = d
        dec += [nn.Linear(last, n_features)]
        self.decoder = nn.Sequential(*dec)

    def forward(self, x):
        return self.decoder(self.encoder(x))


def simulate_sessions(n: int = 2000, seed: int = 42) -> np.ndarray:
    """Plausible normal sessions for cold-start training, in
    ANOMALY_FEATURES order. Replaced by real sessions once collected."""
    rng = np.random.RandomState(seed)
    pre = rng.uniform(3.0, 8.0, n)                       # pre_stress
    improvement = rng.normal(1.5, 1.0, n).clip(-1, 5)    # sessions usually help
    post = (pre - improvement).clip(0, 10)               # post_stress
    data = np.stack([
        pre,
        post,
        post - pre,                                      # delta
        rng.uniform(0.3, 1.0, n),                        # confidence_pre
        rng.uniform(0.3, 1.0, n),                        # confidence_post
        rng.normal(15.0, 4.0, n).clip(5, 40),            # session_duration min
        rng.uniform(0.5, 1.0, n),                        # hrv_agreement
        rng.uniform(0.05, 0.5, n),                       # acoustic_variance
        rng.uniform(0.005, 0.05, n),                     # ambient_rms
        rng.randint(1, 60, n).astype(float),             # session_number
        rng.uniform(6, 23, n),                           # time_of_day
        rng.exponential(2.0, n).clip(0, 30),             # days_since_last
    ], axis=1)
    return data.astype(np.float32)


class SessionAnomalyDetector:
    """Loads a trained autoencoder and scores sessions per user.

    Threshold starts from the global training error distribution and
    becomes personal (the user's own mean + k*std) once the user has
    enough history.
    """

    MIN_PERSONAL_SESSIONS = 5

    def __init__(self, checkpoint_path: str, device: str = "cpu"):
        ckpt = torch.load(checkpoint_path, map_location=device, weights_only=False)
        self.model = SessionAutoencoder(ckpt["n_features"], ckpt["hidden_dims"])
        self.model.load_state_dict(ckpt["state_dict"])
        self.model.eval()
        self.mean = np.asarray(ckpt["feat_mean"], dtype=np.float32)
        self.std = np.asarray(ckpt["feat_std"], dtype=np.float32)
        self.global_threshold = float(ckpt["threshold"])
        self.error_mean = float(ckpt["error_mean"])
        self.error_std = float(ckpt["error_std"])
        # per-user reconstruction error history, in memory
        self.user_errors: dict[str, list[float]] = {}

    def _reconstruction(self, features: np.ndarray):
        x = (features - self.mean) / (self.std + 1e-8)
        x = torch.from_numpy(x.astype(np.float32)).unsqueeze(0)
        with torch.no_grad():
            recon = self.model(x)
        per_dim = ((recon - x) ** 2).squeeze(0).numpy()
        return float(per_dim.mean()), per_dim

    def _threshold_for(self, user_id: str) -> float:
        history = self.user_errors.get(user_id, [])
        if len(history) >= self.MIN_PERSONAL_SESSIONS:
            h = np.asarray(history)
            return float(h.mean() + ANOMALY["threshold_sigma"] * (h.std() + 1e-8))
        return self.global_threshold

    def check(self, user_id: str, features: np.ndarray) -> dict:
        """features: vector in ANOMALY_FEATURES order."""
        features = np.asarray(features, dtype=np.float32).flatten()
        assert features.shape == (len(self.mean),), \
            f"expected {len(self.mean)} features, got {features.shape}"

        error, per_dim = self._reconstruction(features)
        threshold = self._threshold_for(user_id)
        is_anomalous = error > threshold

        ratio = error / (threshold + 1e-8)
        if not is_anomalous:
            severity = "none"
        elif ratio < 1.5:
            severity = "mild"
        elif ratio < 2.5:
            severity = "moderate"
        else:
            severity = "severe"

        # the features that contributed most to the error, as reason codes
        reasons = []
        if is_anomalous:
            top = np.argsort(per_dim)[::-1][:3]
            reasons = [ANOMALY_FEATURES[i] for i in top if per_dim[i] > error]

        # normal sessions extend the user's personal baseline
        if not is_anomalous:
            self.user_errors.setdefault(user_id, []).append(error)

        return {
            "anomaly": bool(is_anomalous),
            "severity": severity,
            "reasons": reasons,
            "error": round(error, 5),
            "threshold": round(threshold, 5),
            "personalised": len(self.user_errors.get(user_id, [])) >= self.MIN_PERSONAL_SESSIONS,
        }
