"""EmoTa parser: Tamil emotional speech (Sri Lankan Tamil).

936 wav utterances, 22 speakers, 5 emotions.
Access: request form at https://rtuthaya.staff.uom.lk/contact-for-resources
Filename convention (verified from the official loader):
    <spkID>_<senID>_<emo>.wav   e.g. 19_18_ang.wav
"""

import argparse
from pathlib import Path

import pandas as pd

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config import EMOTION_VA, STRESSED_EMOTIONS, CALM_EMOTIONS, stress_from_va

# 3-letter emotion codes used in EmoTa filenames -> our canonical names
EMOTION_CODES = {
    "ang": "anger",
    "hap": "happiness",
    "sad": "sadness",
    "fea": "fear",
    "neu": "neutral",
}


def parse_filename(path: Path) -> tuple[str, str] | None:
    """Return (speaker, emotion) from <spkID>_<senID>_<emo>.wav, else None."""
    parts = path.stem.split("_")
    if len(parts) != 3:
        return None
    spk_id, _, emo = parts
    emotion = EMOTION_CODES.get(emo[:3].lower())
    if emotion is None or not spk_id.isdigit():
        return None
    return f"emota_{int(spk_id)}", emotion


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
        parsed = parse_filename(wav)
        if parsed is None:
            continue
        speaker, emotion = parsed
        va = EMOTION_VA[emotion]
        rows.append({
            "path": str(wav),
            "dataset": "emota",
            "language": "ta",
            "speaker": speaker,
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
