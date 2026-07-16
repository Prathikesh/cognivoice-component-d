"""Layer 2b: gated fusion model.

Fuses the frozen emotion2vec embedding with the prosody vector and
regresses valence + arousal. The fusion gate, projections and head are
the trained contribution of this component.
"""

import torch
import torch.nn as nn


class GatedFusionModel(nn.Module):
    """Two-branch fusion: embedding branch + prosody branch.

    A sigmoid gate learns, per dimension and per sample, how much to
    trust each branch. Output is (valence, arousal) in [-1, 1].
    """

    def __init__(self, emb_dim: int, pros_dim: int,
                 proj_dim: int = 128, hidden_dim: int = 64, dropout: float = 0.3):
        super().__init__()
        self.emb_dim = emb_dim
        self.pros_dim = pros_dim

        # each branch projected to the same size so they can be gated
        self.proj_emb = nn.Sequential(
            nn.Linear(emb_dim, proj_dim), nn.LayerNorm(proj_dim), nn.ReLU(),
        )
        self.proj_pros = nn.Sequential(
            nn.Linear(pros_dim, proj_dim), nn.LayerNorm(proj_dim), nn.ReLU(),
        )

        # gate sees both branches and outputs a weight in (0,1) per dimension
        self.gate = nn.Sequential(
            nn.Linear(proj_dim * 2, proj_dim), nn.Sigmoid(),
        )

        # regression head: fused vector -> (valence, arousal)
        self.head = nn.Sequential(
            nn.Linear(proj_dim, hidden_dim), nn.ReLU(), nn.Dropout(dropout),
            nn.Linear(hidden_dim, 2), nn.Tanh(),
        )

    def forward(self, emb: torch.Tensor, pros: torch.Tensor):
        e = self.proj_emb(emb)
        p = self.proj_pros(pros)
        g = self.gate(torch.cat([e, p], dim=-1))
        fused = g * e + (1.0 - g) * p
        out = self.head(fused)
        valence, arousal = out[:, 0], out[:, 1]
        return valence, arousal, g

    def gate_summary(self, emb: torch.Tensor, pros: torch.Tensor) -> float:
        """Mean gate value: near 1 = trusting embeddings, near 0 = prosody."""
        with torch.no_grad():
            _, _, g = self.forward(emb, pros)
        return float(g.mean())


def ccc(pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    """Concordance Correlation Coefficient, the standard V/A metric.

    1.0 = perfect agreement, 0 = none. Unlike plain correlation it also
    punishes scale and mean shifts.
    """
    pred_mean, target_mean = pred.mean(), target.mean()
    pred_var, target_var = pred.var(unbiased=False), target.var(unbiased=False)
    covar = ((pred - pred_mean) * (target - target_mean)).mean()
    return (2 * covar) / (pred_var + target_var + (pred_mean - target_mean) ** 2 + 1e-8)


def ccc_loss(pred_v, pred_a, true_v, true_a) -> torch.Tensor:
    """Loss = 1 - mean CCC over both dimensions, plus a small MSE term
    to stabilise early training when CCC gradients are weak."""
    loss_ccc = 1.0 - 0.5 * (ccc(pred_v, true_v) + ccc(pred_a, true_a))
    loss_mse = 0.5 * ((pred_v - true_v) ** 2 + (pred_a - true_a) ** 2).mean()
    return loss_ccc + 0.2 * loss_mse
