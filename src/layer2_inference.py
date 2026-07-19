"""Layer 2c: inference wrapper - what the API server actually calls.

Loads a trained checkpoint once, keeps the frozen encoder in memory,
and turns raw audio into the final stress report:
    {stress_score 0-10, confidence, valence, arousal, gate_mean}
"""

import sys
from pathlib import Path

import librosa
import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (ENCODER_ABLATIONS, MAX_DURATION_SEC, SAMPLE_RATE,
                    stress_from_va)
from src.layer2_fusion import GatedFusionModel
from src.layer2_prosody import extract_prosody


class StressScorer:
    """audio -> stress report. One instance per server process."""

    def __init__(self, checkpoint_path: str, device: str | None = None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")

        # The checkpoint carries everything needed to rebuild the model:
        # architecture sizes, weights, and the prosody normalisation stats
        # computed at training time (must be identical at inference).
        ckpt = torch.load(checkpoint_path, map_location=self.device,
                          weights_only=False)
        cfg = ckpt["fusion_config"]
        self.model = GatedFusionModel(
            emb_dim=ckpt["emb_dim"], pros_dim=ckpt["pros_dim"],
            proj_dim=cfg["proj_dim"], hidden_dim=cfg["hidden_dim"],
            dropout=cfg["dropout"],
        ).to(self.device)
        self.model.load_state_dict(ckpt["state_dict"])
        self.model.eval()

        self.pros_mean = np.asarray(ckpt["pros_mean"], dtype=np.float32)
        self.pros_std = np.asarray(ckpt["pros_std"], dtype=np.float32)

        # Encoder loads lazily on first request (heavy import + weights),
        # so server startup stays fast.
        self._encoder = None
        self._encoder_id = ENCODER_ABLATIONS[ckpt.get("encoder", "plus_large")]

    def _get_encoder(self):
        if self._encoder is None:
            from funasr import AutoModel
            self._encoder = AutoModel(model=self._encoder_id, hub="ms",
                                      disable_update=True)
        return self._encoder

    def score_array(self, audio: np.ndarray, sr: int = SAMPLE_RATE) -> dict:
        """Score one clip already loaded as a numpy array."""
        if sr != SAMPLE_RATE:
            audio = librosa.resample(audio, orig_sr=sr, target_sr=SAMPLE_RATE)
        audio = np.asarray(audio, dtype=np.float32).flatten()
        audio = audio[: int(MAX_DURATION_SEC * SAMPLE_RATE)]

        # Branch 1: frozen encoder -> utterance-level emotion embedding
        result = self._get_encoder().generate(
            audio, granularity="utterance", extract_embedding=True,
            disable_pbar=True)
        emb = torch.from_numpy(
            np.asarray(result[0]["feats"], dtype=np.float32)).unsqueeze(0)

        # Branch 2: prosody, standardised with the TRAINING-time stats
        pros_raw = extract_prosody(audio)
        pros = (pros_raw - self.pros_mean) / (self.pros_std + 1e-8)
        pros = torch.from_numpy(pros.astype(np.float32)).unsqueeze(0)

        with torch.no_grad():
            v, a, gate = self.model(emb.to(self.device), pros.to(self.device))
        valence, arousal = float(v[0]), float(a[0])

        stress01 = stress_from_va(valence, arousal)
        # Confidence = distance from the ambiguous centre of the V/A plane.
        # A prediction near (0,0) means "could be anything" -> low confidence.
        confidence = float(min(1.0, np.sqrt(valence ** 2 + arousal ** 2)))

        return {
            "stress_score": round(stress01 * 10, 2),
            "confidence": round(confidence, 3),
            "valence": round(valence, 3),
            "arousal": round(arousal, 3),
            "gate_mean": round(float(gate.mean()), 3),
        }

    def score_file(self, path: str) -> dict:
        """Score one audio file of any format/sample rate."""
        audio, sr = librosa.load(path, sr=SAMPLE_RATE, mono=True)
        return self.score_array(audio, sr)
