# CogniVoice — Component D: Voice-Based Stress Detection

Trilingual (English / Sinhala / Tamil) voice stress scoring for the
COGNIFY VR meditation system. A health companion converses with the user
before and after each session; Component D turns those recordings into a
stress level, validates it against HRV, and flags anomalous sessions.

## The five layers

| Layer | File | Technique | Trained by us |
|---|---|---|---|
| 1. Quality gate | `src/layer1_quality.py` | DSP rules (RMS, clipping, SNR) | - |
| 2. Stress scoring | `src/layer2_*.py` | frozen emotion2vec+ prosody branch + **gated fusion + V/A head** | **yes** |
| 3. Pre/post compare | `src/layer3_compare.py` | confidence-weighted statistics | - |
| 4. Cross-modal | `src/layer4_crossmodal.py` | voice vs HRV rules, 4 mismatch types | - |
| 5. Anomaly detection | `src/layer5_anomaly.py` | per-user autoencoder | **yes** |

## Quick start

```bash
# environment (once)
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt

# run all tests
.venv/bin/python -m pytest tests/ -q

# train the anomaly model (fast, local)
.venv/bin/python scripts/train_anomaly.py

# train the fusion model -> use notebooks/colab_train.ipynb on Colab GPU

# run the API server
.venv/bin/uvicorn api_server:app --host 0.0.0.0 --port 8000
```

## Training pipeline (two stages)

1. `scripts/extract_features.py` - run the frozen encoder + prosody over
   every clip once, cache to `.npz` (slow; Colab GPU).
2. `scripts/train_fusion.py` - train the fusion model on the cache
   (fast; minutes).

## Data

Never committed to git. `data/wav/meld` + `data/metadata_meld.csv` are
built by `src/datasets/meld.py`; acted sets by `src/datasets/acted.py`;
EmoTa (Tamil) by `src/datasets/emota.py` once access is granted.

## Docs

- `docs/MASTER.md` - full plain-language explanation of the component
  (restore from tag `v1-backup` history if absent)
- `docs/ABLATION_STUDY.md` - PP1 -> PP2 model comparison for the panel
