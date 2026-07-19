"""Training stage 1: extract and cache features for every clip.

Runs the FROZEN encoder + prosody extractor once per clip and saves
everything to one compressed .npz file. Training (stage 2) then never
touches raw audio again - this is why every later experiment is fast.

This is the slow step: run it on Colab GPU (or overnight on CPU).

Usage:
  python scripts/extract_features.py \
      --metadata data/metadata_meld.csv \
      --out data/features_meld.npz --encoder plus_large
"""

import argparse
import sys
from pathlib import Path

import librosa
import numpy as np
import pandas as pd
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import ENCODER_ABLATIONS, MAX_DURATION_SEC, SAMPLE_RATE
from src.layer2_prosody import N_FEATURES, extract_prosody


def load_encoder(encoder_key: str):
    # Imported here (not top of file) so every other part of this script
    # works on machines without funasr installed.
    from funasr import AutoModel
    model_id = ENCODER_ABLATIONS[encoder_key]
    print(f"loading frozen encoder: {model_id}")
    return AutoModel(model=model_id, hub="ms", disable_update=True)


def embed_clip(encoder, audio: np.ndarray) -> np.ndarray:
    """One clip -> one utterance-level embedding from the frozen encoder."""
    result = encoder.generate(audio, granularity="utterance",
                              extract_embedding=True, disable_pbar=True)
    return np.asarray(result[0]["feats"], dtype=np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--metadata", nargs="+", required=True,
                    help="one or more metadata csvs to process together")
    ap.add_argument("--out", required=True, help="output .npz path")
    ap.add_argument("--encoder", default="plus_large",
                    choices=ENCODER_ABLATIONS)
    args = ap.parse_args()

    meta = pd.concat([pd.read_csv(m) for m in args.metadata],
                     ignore_index=True)
    print(f"{len(meta)} clips from {len(args.metadata)} metadata file(s)")

    encoder = load_encoder(args.encoder)

    embeddings, prosody, kept = [], [], []
    for i, row in tqdm(meta.iterrows(), total=len(meta), desc="extracting"):
        try:
            audio, _ = librosa.load(row["path"], sr=SAMPLE_RATE, mono=True)
            audio = audio[: int(MAX_DURATION_SEC * SAMPLE_RATE)]
            if len(audio) < SAMPLE_RATE:   # skip sub-second fragments
                continue
            embeddings.append(embed_clip(encoder, audio))
            prosody.append(extract_prosody(audio))
            kept.append(i)
        except Exception as e:
            print(f"skip {row['path']}: {e}")

    meta = meta.loc[kept].reset_index(drop=True)
    emb = np.stack(embeddings)
    pros = np.stack(prosody)
    assert pros.shape[1] == N_FEATURES

    # One file carries features + every label/grouping column training needs.
    np.savez_compressed(
        args.out,
        emb=emb, pros=pros,
        valence=meta["valence"].to_numpy(np.float32),
        arousal=meta["arousal"].to_numpy(np.float32),
        stress01=meta["stress01"].to_numpy(np.float32),
        stress_label=meta["stress_label"].to_numpy(np.int64),
        split=meta["split"].to_numpy(str),
        language=meta["language"].to_numpy(str),
        dataset=meta["dataset"].to_numpy(str),
        speaker=meta["speaker"].to_numpy(str),
        encoder=args.encoder,
    )
    print(f"saved {len(meta)} clips -> {args.out}")
    print(f"embedding dim {emb.shape[1]}, prosody dim {pros.shape[1]}")


if __name__ == "__main__":
    main()
