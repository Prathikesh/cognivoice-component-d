"""Layer 3 tests: comparison logic on known score pairs."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.layer3_comparison import compare_scores


def score(stress, conf=0.8):
    return {"stress_score": stress, "confidence": conf}


def test_clear_improvement():
    r = compare_scores(score(7.0), score(3.0))
    assert r["improved"] and r["direction"] == "improved"
    assert r["magnitude"] == "strong"
    assert r["reliable"]


def test_clear_worsening():
    r = compare_scores(score(3.0), score(6.0))
    assert not r["improved"] and r["direction"] == "worsened"


def test_tiny_change_is_noise():
    r = compare_scores(score(5.0), score(4.8))
    assert r["direction"] == "no_reliable_change"
    assert not r["improved"] and not r["reliable"]


def test_low_confidence_widens_noise_band():
    # a 1.2 drop is reliable at high confidence but not at very low
    high = compare_scores(score(6.0, 0.9), score(4.8, 0.9))
    low = compare_scores(score(6.0, 0.1), score(4.8, 0.1))
    assert high["reliable"]
    assert not low["reliable"]


def test_delta_sign():
    r = compare_scores(score(6.0), score(2.0))
    assert r["delta"] == -4.0
