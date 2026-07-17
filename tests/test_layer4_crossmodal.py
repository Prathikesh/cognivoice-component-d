"""Layer 4 tests: scripted agreement and mismatch scenarios."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.layer4_crossmodal import (hrv_stress_score, validate_crossmodal,
                                   MockHRVProvider, StoredHRVProvider)


def test_hrv_mapping_direction():
    # lower RMSSD means more stressed
    assert hrv_stress_score(25.0) > hrv_stress_score(70.0)
    assert 0 <= hrv_stress_score(10.0) <= 10
    assert 0 <= hrv_stress_score(100.0) <= 10


def test_agreement_case():
    # voice improves 7->3, hrv improves 30ms->65ms: everything agrees
    r = validate_crossmodal(7.0, 3.0, 30.0, 65.0)
    assert r["validated"]
    assert r["mismatch_type"] is None
    assert r["agreement"] > 0.5


def test_cognitive_persistence():
    # body recovered (hrv better) but voice stays stressed
    r = validate_crossmodal(7.0, 7.0, 30.0, 75.0)
    assert not r["validated"]
    assert r["mismatch_type"] == "cognitive_persistence"


def test_vocal_masking():
    # voice claims recovery, body still stressed
    r = validate_crossmodal(6.5, 3.0, 38.0, 36.0)
    assert not r["validated"]
    assert r["mismatch_type"] == "vocal_masking"


def test_baseline_divergence():
    # signals far apart at both time points
    r = validate_crossmodal(1.0, 1.0, 22.0, 24.0)
    assert not r["validated"]
    assert r["mismatch_type"] == "baseline_divergence"


def test_providers():
    mock = MockHRVProvider(pre_rmssd=35, post_rmssd=55)
    assert mock.get_rmssd("any", "pre") == 35
    store = StoredHRVProvider()
    assert store.get_rmssd("s1", "pre") is None
    store.push("s1", "pre", 42.0)
    assert store.get_rmssd("s1", "pre") == 42.0
