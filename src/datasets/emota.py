"""EmoTa parser: Tamil emotional speech (Sri Lankan Tamil).

936 wav utterances, 22 speakers, 5 emotions.
Download: https://github.com/aaivu/EmoTa

Note: the exact folder/filename layout must be checked after download.
This parser handles the two common layouts: emotion subfolders, or
emotion codes inside filenames. Adjust EMOTION_KEYWORDS if needed.
"""

import argparse
import re
from pathlib import Path

import pandas as pd

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config import EMOTION_VA, STRESSED_EMOTIONS, CALM_EMOTIONS, stress_from_va

# keywords/codes that identify each emotion in paths or filenames
EMOTION_KEYWORDS = {
    "anger": ["anger", "angry", "ang"],
    "happiness": ["happy", "happiness", "hap", "joy"],
    "sadness": ["sad", "sadness"],
    "fear": ["fear", "fearful", "fea"],
    "neutral": ["neutral", "neu"],
}


def detect_emotion(path: Path) -> str | None:
    # check folder names first, then the filename itself
    text = "/".join(p.lower() for p in path.parts)
    for emotion, keys in EMOTION_KEYWORDS.items():
        for k in keys:
            if re.search(rf"(^|[/_\-\.]){k}([/_\-\.]|$)", text):
                return emotion
    return None


def detect_speaker(path: Path) -> str:
    # EmoTa encodes a speaker id; look for a number pattern in the filename
    m = re.search(r"(?:spk|speaker|s)?[_\-]?(\d{1,2})[_\-]", path.name.lower())
    return f"emota_{m.group(1)}" if m else f"emota_{path.parent.name}"


def binary_stress_label(emotion: str) -> int:
    if emotion in STRESSED_EMOTIONS:
        return 1
    if emotion in CALM_EMOTIONS:
        return 0
    return -1


def build_metadata(emota_root: Path, test_speaker_ratio: float = 0.2) -> pd.DataFrame:
    """Scan all wavs, label them, and make a speaker-independent split."""
    rows = []
    for wav in sorted(emota_root.rglob("*.wav")):
        emotion = detect_emotion(wav)
        if emotion is None:
            continue
        va = EMOTION_VA[emotion]
        rows.append({
            "path": str(wav),
            "dataset": "emota",
            "language": "ta",
            "speaker": detect_speaker(wav),
            "emotion": emotion,
            "valence": va["valence"],
            "arousal": va["arousal"],
            "stress01": stress_from_va(va["valence"], va["arousal"]),
            "stress_label": binary_stress_label(emotion),
        })
    df = pd.DataFrame(rows)
    if df.empty:
        return df

    # speaker-independent split: whole speakers go to test, never mixed
    speakers = sorted(df["speaker"].unique())
    n_test = max(1, int(len(speakers) * test_speaker_ratio))
    test_speakers = set(speakers[-n_test:])
    df["split"] = df["speaker"].apply(lambda s: "test" if s in test_speakers else "train")
    return df


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Build EmoTa metadata csv")
    ap.add_argument("--emota-root", required=True, help="root folder of the EmoTa wavs")
    ap.add_argument("--out", required=True, help="output metadata csv path")
    args = ap.parse_args()

    meta = build_metadata(Path(args.emota_root))
    meta.to_csv(args.out, index=False)
    print(f"wrote {len(meta)} rows to {args.out}")
    if len(meta):
        print(meta.groupby(["split", "emotion"]).size())
        print(f"speakers: {meta['speaker'].nunique()}")
