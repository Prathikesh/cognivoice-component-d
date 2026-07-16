# CogniVoice — Component D: Voice-Based Stress Detection (v2)

Trilingual (English / Sinhala / Tamil) voice stress scoring for the COGNIFY VR
meditation system. This is the PP2 rebuild of Component D: a **trained**
fusion model replaces the PP1 approach of directly using a pretrained
classifier with a hand-written emotion→stress lookup table.

## Architecture

```
audio (16 kHz mono, EN / SI / TA)
     ├──► emotion2vec (FROZEN)          ──► 768-d emotion embedding
     └──► prosody extractor (trainable   ──► ~24-d language-independent features
          branch input: F0, jitter,          (pitch, jitter, shimmer, HNR,
          shimmer, HNR, energy, rate,         energy, speech rate, pauses)
          pauses — parselmouth + librosa)
                      │
          Gated fusion layer   ← TRAINED (ours)
                      │
          MLP regression head  ← TRAINED (ours)
                      │
          valence + arousal (learned)  ← replaces PP1 lookup table
                      │
          stress score 0–10 + confidence
```

**Why this design**

- PP1 ablations (see [docs/PP1_SUMMARY.md](docs/PP1_SUMMARY.md)) showed the
  encoder was not the bottleneck — the acted-speech domain gap was. Models
  trained purely on RAVDESS/CREMA-D/TESS hit 84.7% on acted test sets and
  still failed on real spontaneous voices.
- Prosodic stress markers (F0 rise, jitter, tempo change) are physiological
  and language-independent → this branch carries Sinhala/Tamil transfer
  without a cross-lingual ASR encoder (XLSR was tried in PP1 and
  underperformed emotion-specialised encoders).
- The head learns **arousal/valence regression** on naturalistic corpora and
  stress is derived via Russell's circumplex (high arousal × negative
  valence), because public data is labelled with emotion/VA, not "stress".

## Repository layout

```
config.py                 central paths + label maps + hyperparameters
src/prosody_features.py   prosodic feature extraction (parselmouth + librosa)
src/fusion_model.py       gated fusion + MLP head + CCC loss (PyTorch)
src/datasets/meld.py      MELD parser → unified metadata (emotion → V/A → stress)
scripts/extract_features.py   cache emotion2vec embeddings + prosody → .npz
scripts/train_fusion.py       train fusion head on cached features
notebooks/kaggle_train.ipynb  thin GPU runner (clone → install → train → save)
docs/PP1_SUMMARY.md       what was built and learned in PP1
```

## Workflow

- **Local (this repo, git):** all source code, API, integration. No GPU needed.
- **Kaggle/Colab (free GPU):** feature extraction + training only, via the
  notebook runner. Checkpoints uploaded to Drive/HF Hub, downloaded locally.
- **Data:** never committed. MELD & co. live as Kaggle Datasets; local copies
  go on the external drive.

## Quick start

```bash
pip install -r requirements.txt
# 1. Build MELD metadata (after downloading MELD.Raw)
python -m src.datasets.meld --meld-root /path/to/MELD.Raw --out data/metadata_meld.csv
# 2. Extract & cache features (GPU recommended — run on Kaggle)
python scripts/extract_features.py --metadata data/metadata_meld.csv --out data/features_meld.npz
# 3. Train
python scripts/train_fusion.py --features data/features_meld.npz --out models/fusion_v2.pt
```

## Component D in COGNIFY (integration contract)

Component D is a black box behind a REST API (to be ported from PP1):

- **Inbound (Component B / HRV):** `POST /session-update`
  `{"rmssd": float, "timestamp": iso8601, "phase": "pre|during|post"}`
- **Outbound (Component C / Unity):** from `/full-session` →
  `{"stress_level": 0-10, "confidence": 0-1, "anomaly_flag": bool}`
