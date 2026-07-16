"""Central configuration for Component D. Every script imports from here."""

from pathlib import Path

# ---------- paths ----------
ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"           # gitignored, datasets live here locally
MODELS_DIR = ROOT / "models"       # gitignored, checkpoints live here
DATA_DIR.mkdir(exist_ok=True)
MODELS_DIR.mkdir(exist_ok=True)

# ---------- audio ----------
SAMPLE_RATE = 16000                # all audio resampled to 16 kHz mono
MIN_DURATION_SEC = 1.0             # clips shorter than this are rejected
MAX_DURATION_SEC = 35.0            # clips longer than this are trimmed

# ---------- layer 1: ambient quality gate ----------
AMBIENT = {
    "min_rms": 0.005,              # below this = too quiet / no speech
    "max_rms": 0.5,                # above this = too loud / mic overload
    "max_clip_ratio": 0.01,        # fraction of samples at digital max allowed
    "max_flatness": 0.4,           # high spectral flatness = pure noise, no speech
    "min_snr_db": 10.0,            # estimated speech-to-noise ratio floor
}

# ---------- layer 2: encoder + fusion model ----------
# frozen pretrained encoder, used only as a feature extractor
EMOTION2VEC_MODEL_ID = "iic/emotion2vec_plus_large"   # 1024-d embeddings
# smaller alternatives for the ablation table
EMOTION2VEC_ABLATIONS = {
    "plus_large": "iic/emotion2vec_plus_large",
    "plus_base": "iic/emotion2vec_plus_base",
    "base_finetuned": "iic/emotion2vec_base_finetuned",
}

FUSION = {
    "proj_dim": 128,               # both branches projected to this size
    "hidden_dim": 64,              # MLP head hidden layer
    "dropout": 0.3,
}

TRAINING = {
    "batch_size": 64,
    "lr": 1e-3,
    "weight_decay": 1e-4,
    "max_epochs": 100,
    "early_stop_patience": 10,     # stop if val CCC does not improve
}

# ---------- emotion -> valence/arousal mapping ----------
# circumplex coordinates in [-1, 1], used to derive training targets
# from categorical emotion labels (MELD, EmoTa, acted sets)
EMOTION_VA = {
    "neutral":   {"valence":  0.0, "arousal":  0.0},
    "joy":       {"valence":  0.7, "arousal":  0.5},
    "happiness": {"valence":  0.7, "arousal":  0.5},
    "surprise":  {"valence":  0.3, "arousal":  0.7},
    "anger":     {"valence": -0.6, "arousal":  0.8},
    "fear":      {"valence": -0.7, "arousal":  0.8},
    "sadness":   {"valence": -0.6, "arousal": -0.4},
    "disgust":   {"valence": -0.6, "arousal":  0.4},
    "calm":      {"valence":  0.4, "arousal": -0.5},
}

# emotions that give a clean binary stress label for evaluation
# (ambiguous ones like surprise/disgust are excluded from binary metrics)
STRESSED_EMOTIONS = {"anger", "fear"}
CALM_EMOTIONS = {"neutral", "joy", "happiness", "calm"}


def stress_from_va(valence: float, arousal: float) -> float:
    """Stress in [0, 1]: high arousal combined with negative valence.

    Both factors are rescaled to [0, 1] and multiplied, so stress is high
    only when arousal is high AND valence is negative (Russell circumplex).
    """
    arousal01 = (arousal + 1.0) / 2.0
    negativity01 = (1.0 - valence) / 2.0
    return arousal01 * negativity01


# ---------- layer 5: anomaly detection ----------
ANOMALY_FEATURES = [
    "pre_stress", "post_stress", "delta", "confidence_pre", "confidence_post",
    "session_duration", "hrv_agreement", "acoustic_variance", "ambient_rms",
    "session_number", "time_of_day", "days_since_last",
]
ANOMALY = {
    "hidden_dims": [16, 8, 4],     # encoder side, mirrored for decoder
    "threshold_sigma": 3.0,        # per-user threshold = mean + sigma * std
    "min_sessions_for_lstm": 5,    # switch to LSTM-AE after this many sessions
}
