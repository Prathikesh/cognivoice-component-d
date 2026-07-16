"""Stage 2: train the gated fusion model on cached features.

Fast step: ~1-2M trainable params, minutes on any GPU or even CPU.

Usage:
  python scripts/train_fusion.py --features data/features_meld.npz \
      --out models/fusion_v2.pt
  # multilingual fine-tune: pass several npz files together
  python scripts/train_fusion.py --features data/features_meld.npz \
      data/features_emota.npz --out models/fusion_v2_multi.pt
"""

import argparse
import json
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader, TensorDataset
from sklearn.metrics import accuracy_score, f1_score

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import FUSION, TRAINING, MODELS_DIR
from src.fusion_model import GatedFusionModel, ccc, ccc_loss


def load_features(paths: list[str]) -> dict:
    """Load one or more npz files and concatenate them."""
    parts = [np.load(p, allow_pickle=False) for p in paths]
    keys = ["emb", "pros", "valence", "arousal", "stress01", "stress_label",
            "split", "language"]
    data = {k: np.concatenate([p[k] for p in parts]) for k in keys}
    print(f"loaded {len(data['emb'])} clips, "
          f"emb dim {data['emb'].shape[1]}, pros dim {data['pros'].shape[1]}")
    return data


def make_loaders(data: dict):
    """Standardise prosody on train stats, return loaders + the stats."""
    train_mask = data["split"] == "train"
    val_mask = data["split"] == "val"
    if not val_mask.any():
        # datasets without a val split: carve 10% off train, deterministic
        rng = np.random.RandomState(42)
        idx = np.where(train_mask)[0]
        val_idx = rng.choice(idx, size=max(1, len(idx) // 10), replace=False)
        val_mask = np.zeros_like(train_mask)
        val_mask[val_idx] = True
        train_mask = train_mask & ~val_mask
    test_mask = data["split"] == "test"

    # prosody features have wildly different scales, so standardise them;
    # stats come from train only to avoid leakage
    mean = data["pros"][train_mask].mean(axis=0)
    std = data["pros"][train_mask].std(axis=0) + 1e-8
    pros = (data["pros"] - mean) / std

    def subset(mask):
        return TensorDataset(
            torch.from_numpy(data["emb"][mask]),
            torch.from_numpy(pros[mask].astype(np.float32)),
            torch.from_numpy(data["valence"][mask]),
            torch.from_numpy(data["arousal"][mask]),
            torch.from_numpy(data["stress_label"][mask]),
        )

    bs = TRAINING["batch_size"]
    loaders = {
        "train": DataLoader(subset(train_mask), batch_size=bs, shuffle=True),
        "val": DataLoader(subset(val_mask), batch_size=bs),
        "test": DataLoader(subset(test_mask), batch_size=bs) if test_mask.any() else None,
    }
    print(f"train {train_mask.sum()}, val {val_mask.sum()}, test {test_mask.sum()}")
    return loaders, mean, std


@torch.no_grad()
def evaluate(model, loader, device) -> dict:
    """CCC for valence/arousal plus binary stress accuracy and F1."""
    model.eval()
    pv, pa, tv, ta, labels = [], [], [], [], []
    for emb, pros, v, a, y in loader:
        out_v, out_a, _ = model(emb.to(device), pros.to(device))
        pv.append(out_v.cpu()); pa.append(out_a.cpu())
        tv.append(v); ta.append(a); labels.append(y)
    pv, pa = torch.cat(pv), torch.cat(pa)
    tv, ta, labels = torch.cat(tv), torch.cat(ta), torch.cat(labels)

    metrics = {
        "ccc_valence": float(ccc(pv, tv)),
        "ccc_arousal": float(ccc(pa, ta)),
    }
    # binary stress check on rows with a clean stressed/calm label
    mask = labels >= 0
    if mask.any():
        # same formula as config.stress_from_va, in torch
        stress = ((pa[mask] + 1) / 2) * ((1 - pv[mask]) / 2)
        pred = (stress > 0.35).long()  # 0.35 sits between calm (~0.25) and stressed (~0.7)
        metrics["stress_acc"] = float(accuracy_score(labels[mask], pred))
        metrics["stress_f1"] = float(f1_score(labels[mask], pred, zero_division=0))
    return metrics


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--features", nargs="+", required=True)
    ap.add_argument("--out", default=str(MODELS_DIR / "fusion_v2.pt"))
    ap.add_argument("--epochs", type=int, default=TRAINING["max_epochs"])
    ap.add_argument("--lr", type=float, default=TRAINING["lr"])
    args = ap.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"device: {device}")

    data = load_features(args.features)
    loaders, pros_mean, pros_std = make_loaders(data)

    model = GatedFusionModel(
        emb_dim=data["emb"].shape[1], pros_dim=data["pros"].shape[1],
        proj_dim=FUSION["proj_dim"], hidden_dim=FUSION["hidden_dim"],
        dropout=FUSION["dropout"],
    ).to(device)
    n_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"trainable parameters: {n_params:,}")

    opt = torch.optim.AdamW(model.parameters(), lr=args.lr,
                            weight_decay=TRAINING["weight_decay"])

    best_val, patience, history = -1e9, 0, []
    for epoch in range(args.epochs):
        model.train()
        total = 0.0
        for emb, pros, v, a, _ in loaders["train"]:
            emb, pros = emb.to(device), pros.to(device)
            v, a = v.to(device), a.to(device)
            opt.zero_grad()
            pred_v, pred_a, _ = model(emb, pros)
            loss = ccc_loss(pred_v, pred_a, v, a)
            loss.backward()
            opt.step()
            total += float(loss)

        val = evaluate(model, loaders["val"], device)
        val_score = val["ccc_valence"] + val["ccc_arousal"]
        history.append({"epoch": epoch, "train_loss": total / len(loaders["train"]), **val})
        print(f"epoch {epoch:3d}  loss {total/len(loaders['train']):.4f}  "
              f"val ccc V {val['ccc_valence']:.3f} A {val['ccc_arousal']:.3f}")

        if val_score > best_val:
            best_val, patience = val_score, 0
            torch.save({
                "state_dict": model.state_dict(),
                "emb_dim": data["emb"].shape[1],
                "pros_dim": data["pros"].shape[1],
                "fusion_config": FUSION,
                "pros_mean": pros_mean, "pros_std": pros_std,
                "encoder": "plus_large",
                "val_metrics": val,
            }, args.out)
        else:
            patience += 1
            if patience >= TRAINING["early_stop_patience"]:
                print("early stopping")
                break

    # final report on the held-out test split, per language when possible
    ckpt = torch.load(args.out, map_location=device, weights_only=False)
    model.load_state_dict(ckpt["state_dict"])
    if loaders["test"] is not None:
        test = evaluate(model, loaders["test"], device)
        print("test:", json.dumps(test, indent=2))
        ckpt["test_metrics"] = test
        torch.save(ckpt, args.out)

    hist_path = Path(args.out).with_suffix(".history.json")
    hist_path.write_text(json.dumps(history, indent=2))
    print(f"saved model -> {args.out}\nsaved history -> {hist_path}")


if __name__ == "__main__":
    main()
