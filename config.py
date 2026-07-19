"""Central configuration for Component D.

Every module imports settings from here. Change a threshold or a model
in ONE place and the whole system follows.
"""

from pathlib import Path

# ---------------------------------------------------------------- paths
ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"        # datasets (gitignored, never pushed)
MODELS_DIR = ROOT / "models"    # trained checkpoints (gitignored)
DATA_DIR.mkdir(exist_ok=True)
MODELS_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------- audio
# Every clip is resampled to this before touching any model.
SAMPLE_RATE = 16000
MIN_DURATION_SEC = 1.0          # shorter clips are rejected by Layer 1
MAX_DURATION_SEC = 35.0         # longer clips are trimmed

# --------------------------------------------- layer 1: quality gate
# Thresholds tuned for consumer microphones (phone / Quest 2 headset).
QUALITY = {
    "min_rms": 0.005,           # below = silence / mic muted
    "max_rms": 0.5,             # above = mic overload
    "max_clip_ratio": 0.01,     # >1% samples at digital ceiling = distortion
    "max_flatness": 0.4,        # spectral flatness near 1 = noise, not speech
    "min_snr_db": 10.0,         # speech must stand 10 dB above noise floor
}

# --------------------------------------------- layer 2: stress model
# The frozen encoder. plus_large = 300M params trained on 42,500 hours
# of emotional speech; we use it ONLY as a feature extractor.
ENCODER_ID = "iic/emotion2vec_plus_large"

# Alternatives kept for the ablation table (same code path, one flag).
ENCODER_ABLATIONS = {
    "plus_large": "iic/emotion2vec_plus_large",       # 1024-d embedding
    "plus_base": "iic/emotion2vec_plus_base",         # 768-d, 90M params
    "base_finetuned": "iic/emotion2vec_base_finetuned",  # the PP1 encoder
}

# Architecture of the parts WE train (fusion gate + regression head).
FUSION = {
    "proj_dim": 128,            # both branches projected to this width
    "hidden_dim": 64,           # head hidden layer
    "dropout": 0.3,
}

TRAINING = {
    "batch_size": 64,
    "lr": 1e-3,
    "weight_decay": 1e-4,
    "max_epochs": 100,
    "early_stop_patience": 10,  # stop when validation CCC stops improving
}

# ------------------------------- emotion -> valence/arousal targets
# Public datasets label emotions, not stress. We map each emotion to
# coordinates on Russell's circumplex (valence = pleasant<->unpleasant,
# arousal = calm<->activated), both in [-1, 1]. The model learns to
# predict these two numbers; stress is derived from them below.
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

# Emotions with an unambiguous stressed/calm reading, used ONLY for
# binary evaluation metrics (surprise/disgust/sadness are excluded).
STRESSED_EMOTIONS = {"anger", "fear"}
CALM_EMOTIONS = {"neutral", "joy", "happiness", "calm"}


def stress_from_va(valence: float, arousal: float) -> float:
    """Stress in [0, 1] from predicted valence/arousal.

    Psychological definition: stress = high arousal AND negative valence.
    Multiplying the two rescaled factors means BOTH must be present -
    excited-happy (high arousal, positive valence) is NOT stress.
    """
    arousal01 = (arousal + 1.0) / 2.0        # [-1,1] -> [0,1]
    negativity01 = (1.0 - valence) / 2.0     # +1 valence -> 0, -1 -> 1
    return arousal01 * negativity01


# --------------------------------------------- layer 5: anomaly model
# The 12 numbers that summarise one complete session. Order matters:
# the autoencoder and every caller use exactly this order.
ANOMALY_FEATURES = [
    "pre_stress", "post_stress", "delta",
    "confidence_pre", "confidence_post",
    "session_duration", "hrv_agreement", "acoustic_variance",
    "ambient_rms", "session_number", "time_of_day", "days_since_last",
]
ANOMALY = {
    "hidden_dims": [16, 8, 4],  # encoder widths; decoder mirrors them
    "threshold_sigma": 3.0,     # anomaly if error > mean + 3*std
    "min_personal_sessions": 5, # switch to per-user threshold after this
}
