"""Train the Layer 5 session autoencoder.

Cold-start version trains on simulated sessions; rerun with
--sessions-csv once real session data exists.

Usage:
  python scripts/train_anomaly.py --out models/anomaly_v2.pt
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import torch

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import ANOMALY, ANOMALY_FEATURES, MODELS_DIR
from src.layer5_anomaly import SessionAutoencoder, simulate_sessions


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(MODELS_DIR / "anomaly_v2.pt"))
    ap.add_argument("--sessions-csv", default=None,
                    help="csv of real sessions with ANOMALY_FEATURES columns")
    ap.add_argument("--epochs", type=int, default=200)
    args = ap.parse_args()

    if args.sessions_csv:
        df = pd.read_csv(args.sessions_csv)
        data = df[ANOMALY_FEATURES].to_numpy(np.float32)
        print(f"training on {len(data)} real sessions")
    else:
        data = simulate_sessions(2000)
        print("training on 2000 simulated sessions (cold start)")

    # standardise, keep the stats for inference
    mean, std = data.mean(axis=0), data.std(axis=0) + 1e-8
    x = torch.from_numpy((data - mean) / std)

    model = SessionAutoencoder(len(ANOMALY_FEATURES), ANOMALY["hidden_dims"])
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)

    for epoch in range(args.epochs):
        opt.zero_grad()
        recon = model(x)
        loss = ((recon - x) ** 2).mean()
        loss.backward()
        opt.step()
        if epoch % 50 == 0:
            print(f"epoch {epoch:3d}  loss {float(loss):.5f}")

    # global threshold from the training error distribution
    model.eval()
    with torch.no_grad():
        errors = ((model(x) - x) ** 2).mean(dim=1).numpy()
    threshold = float(errors.mean() + ANOMALY["threshold_sigma"] * errors.std())

    torch.save({
        "state_dict": model.state_dict(),
        "n_features": len(ANOMALY_FEATURES),
        "hidden_dims": ANOMALY["hidden_dims"],
        "feat_mean": mean, "feat_std": std,
        "threshold": threshold,
        "error_mean": float(errors.mean()), "error_std": float(errors.std()),
        "trained_on": "real" if args.sessions_csv else "simulated",
    }, args.out)
    print(f"saved -> {args.out}  (threshold {threshold:.5f})")


if __name__ == "__main__":
    main()
