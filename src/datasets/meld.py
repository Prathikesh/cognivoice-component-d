"""MELD parser: naturalistic English conversational speech.

MELD ships as CSV label files plus video clips (.mp4). Audio must be
extracted to wav first (see extract_audio). Output is a unified
metadata CSV shared by all datasets in this project.

Download: https://affective-meld.github.io (MELD.Raw.tar.gz)
"""

import argparse
import subprocess
from pathlib import Path

import pandas as pd

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config import EMOTION_VA, STRESSED_EMOTIONS, CALM_EMOTIONS, stress_from_va

# MELD csv emotion names -> our canonical names in EMOTION_VA
MELD_EMOTION_MAP = {
    "neutral": "neutral",
    "joy": "joy",
    "surprise": "surprise",
    "anger": "anger",
    "fear": "fear",
    "sadness": "sadness",
    "disgust": "disgust",
}

# csv filename and clip folder per split, as shipped in MELD.Raw
SPLITS = {
    "train": ("train_sent_emo.csv", "train_splits"),
    "val": ("dev_sent_emo.csv", "dev_splits_complete"),
    "test": ("test_sent_emo.csv", "output_repeated_splits_test"),
}


def binary_stress_label(emotion: str) -> int:
    # 1 = stressed, 0 = calm, -1 = ambiguous (excluded from binary metrics)
    if emotion in STRESSED_EMOTIONS:
        return 1
    if emotion in CALM_EMOTIONS:
        return 0
    return -1


def extract_audio(mp4_path: Path, wav_path: Path) -> bool:
    """Convert one clip to 16 kHz mono wav with ffmpeg."""
    wav_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-y", "-i", str(mp4_path),
           "-ar", "16000", "-ac", "1", "-loglevel", "error", str(wav_path)]
    return subprocess.run(cmd).returncode == 0


def build_metadata(meld_root: Path, wav_dir: Path, convert: bool = False) -> pd.DataFrame:
    """Walk all three splits and produce one metadata dataframe."""
    rows = []
    for split, (csv_name, clip_dir) in SPLITS.items():
        csv_path = meld_root / csv_name
        if not csv_path.exists():
            print(f"warning: {csv_path} not found, skipping split '{split}'")
            continue
        df = pd.read_csv(csv_path)
        for _, r in df.iterrows():
            emotion = MELD_EMOTION_MAP.get(str(r["Emotion"]).lower())
            if emotion is None:
                continue
            clip = f"dia{r['Dialogue_ID']}_utt{r['Utterance_ID']}"
            mp4 = meld_root / clip_dir / f"{clip}.mp4"
            wav = wav_dir / split / f"{clip}.wav"

            if convert and mp4.exists() and not wav.exists():
                extract_audio(mp4, wav)
            if not wav.exists():
                continue  # only keep rows whose audio really exists

            va = EMOTION_VA[emotion]
            rows.append({
                "path": str(wav),
                "dataset": "meld",
                "language": "en",
                "split": split,
                "speaker": f"meld_{r.get('Speaker', 'unknown')}",
                "emotion": emotion,
                "valence": va["valence"],
                "arousal": va["arousal"],
                "stress01": stress_from_va(va["valence"], va["arousal"]),
                "stress_label": binary_stress_label(emotion),
            })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Build MELD metadata csv")
    ap.add_argument("--meld-root", required=True, help="folder containing MELD csvs and clip folders")
    ap.add_argument("--wav-dir", required=True, help="where extracted wav files live / will go")
    ap.add_argument("--out", required=True, help="output metadata csv path")
    ap.add_argument("--convert", action="store_true", help="run ffmpeg mp4->wav conversion")
    args = ap.parse_args()

    meta = build_metadata(Path(args.meld_root), Path(args.wav_dir), args.convert)
    meta.to_csv(args.out, index=False)
    print(f"wrote {len(meta)} rows to {args.out}")
    if len(meta):
        print(meta.groupby(["split", "emotion"]).size())
