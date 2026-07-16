"""Layer 2c: inference wrapper around the trained fusion model.

This is the class the API server uses: audio file in, stress report out.
Loads the frozen encoder once and keeps it in memory.
"""

import numpy as np
import torch
import librosa

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (EMOTION2VEC_ABLATIONS, SAMPLE_RATE, MAX_DURATION_SEC,
                    stress_from_va)
from src.fusion_model import GatedFusionModel
from src.prosody_features import extract_prosody


class StressScorer:
    """audio -> {stress 0-10, confidence, valence, arousal}"""

    def __init__(self, checkpoint_path: str, device: str | None = None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")

        ckpt = torch.load(checkpoint_path, map_location=self.device, weights_only=False)
        cfg = ckpt["fusion_config"]
        self.model = GatedFusionModel(
            emb_dim=ckpt["emb_dim"], pros_dim=ckpt["pros_dim"],
            proj_dim=cfg["proj_dim"], hidden_dim=cfg["hidden_dim"],
            dropout=cfg["dropout"],
        ).to(self.device)
        self.model.load_state_dict(ckpt["state_dict"])
        self.model.eval()

        # prosody standardisation stats saved at training time
        self.pros_mean = np.asarray(ckpt["pros_mean"], dtype=np.float32)
        self.pros_std = np.asarray(ckpt["pros_std"], dtype=np.float32)

        # frozen encoder, loaded lazily on first call (slow import)
        self._encoder = None
        self._encoder_id = EMOTION2VEC_ABLATIONS[ckpt.get("encoder", "plus_large")]

    def _get_encoder(self):
        if self._encoder is None:
            from funasr import AutoModel
            self._encoder = AutoModel(model=self._encoder_id, hub="ms",
                                      disable_update=True)
        return self._encoder

    def score_array(self, audio: np.ndarray, sr: int = SAMPLE_RATE) -> dict:
        if sr != SAMPLE_RATE:
            audio = librosa.resample(audio, orig_sr=sr, target_sr=SAMPLE_RATE)
        audio = np.asarray(audio, dtype=np.float32).flatten()
        audio = audio[: int(MAX_DURATION_SEC * SAMPLE_RATE)]

        res = self._get_encoder().generate(
            audio, granularity="utterance", extract_embedding=True,
            disable_pbar=True)
        emb = torch.from_numpy(
            np.asarray(res[0]["feats"], dtype=np.float32)).unsqueeze(0)

        pros_raw = extract_prosody(audio)
        pros = (pros_raw - self.pros_mean) / (self.pros_std + 1e-8)
        pros = torch.from_numpy(pros.astype(np.float32)).unsqueeze(0)

        with torch.no_grad():
            v, a, gate = self.model(emb.to(self.device), pros.to(self.device))
        valence, arousal = float(v[0]), float(a[0])

        stress01 = stress_from_va(valence, arousal)
        # confidence: how far the prediction sits from the ambiguous centre
        confidence = float(min(1.0, np.sqrt(valence ** 2 + arousal ** 2)))

        return {
            "stress_score": round(stress01 * 10, 2),      # 0-10 for the app
            "confidence": round(confidence, 3),
            "valence": round(valence, 3),
            "arousal": round(arousal, 3),
            "gate_mean": round(float(gate.mean()), 3),     # 1=embeddings, 0=prosody
        }

    def score_file(self, path: str) -> dict:
        audio, sr = librosa.load(path, sr=SAMPLE_RATE, mono=True)
        return self.score_array(audio, sr)
