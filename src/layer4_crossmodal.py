"""Layer 4: cross-modal validation of voice stress against HRV.

Component B (wearable) supplies HRV; we check whether the two
independent stress signals agree, and classify the mismatch when they
do not. Rule-based by design: explainable, and no labelled corpus of
voice-HRV mismatches exists to train on.
"""


class HRVProvider:
    """Interface Component B implements. RMSSD in milliseconds."""

    def get_rmssd(self, session_id: str, phase: str) -> float | None:
        raise NotImplementedError


class MockHRVProvider(HRVProvider):
    """Stand-in for demos and tests: mildly stressed pre, recovered post."""

    def __init__(self, pre_rmssd: float = 35.0, post_rmssd: float = 55.0):
        self.values = {"pre": pre_rmssd, "post": post_rmssd}

    def get_rmssd(self, session_id: str, phase: str) -> float | None:
        return self.values.get(phase)


class StoredHRVProvider(HRVProvider):
    """Real provider: Component B pushes values via the /session-update
    endpoint and we read them back here."""

    def __init__(self):
        self.store: dict[tuple[str, str], float] = {}

    def push(self, session_id: str, phase: str, rmssd: float):
        self.store[(session_id, phase)] = rmssd

    def get_rmssd(self, session_id: str, phase: str) -> float | None:
        return self.store.get((session_id, phase))


def hrv_stress_score(rmssd: float) -> float:
    """Map RMSSD to a 0-10 stress proxy. Lower RMSSD = higher stress.
    Typical resting adult RMSSD roughly spans 20 (stressed) to 80 (relaxed)."""
    score01 = (80.0 - rmssd) / 60.0
    return round(min(1.0, max(0.0, score01)) * 10, 2)


# levels differing by more than this (0-10 scale) count as disagreement
LEVEL_TOLERANCE = 3.0


def validate_crossmodal(voice_pre: float, voice_post: float,
                        hrv_pre_rmssd: float, hrv_post_rmssd: float) -> dict:
    """Compare voice and HRV stress at both time points plus their trends."""
    hrv_pre = hrv_stress_score(hrv_pre_rmssd)
    hrv_post = hrv_stress_score(hrv_post_rmssd)

    voice_trend = voice_post - voice_pre
    hrv_trend = hrv_post - hrv_pre
    # trends agree when both move the same way, or both are near-flat
    trends_agree = (voice_trend * hrv_trend > 0) or \
                   (abs(voice_trend) < 1.0 and abs(hrv_trend) < 1.0)

    pre_agree = abs(voice_pre - hrv_pre) <= LEVEL_TOLERANCE
    post_agree = abs(voice_post - hrv_post) <= LEVEL_TOLERANCE

    # mismatch typing: trend disagreement carries the most meaning,
    # so it is classified first, then level divergences
    mismatch = None
    if not trends_agree:
        if voice_trend < hrv_trend:
            mismatch = "vocal_masking"        # voice sounds calmer than the body is
        else:
            mismatch = "cognitive_persistence"  # body recovered, voice still stressed
    elif not pre_agree and not post_agree:
        mismatch = "baseline_divergence"      # the two signals disagree throughout
    elif not post_agree:
        mismatch = "outcome_divergence"       # agreed before, disagree after
    elif not pre_agree:
        mismatch = "baseline_divergence"      # disagreed at the start only

    # agreement in [0,1]: mean closeness of the two signals at both points
    closeness = 1.0 - (abs(voice_pre - hrv_pre) + abs(voice_post - hrv_post)) / 20.0
    agreement = round(max(0.0, closeness), 3)

    return {
        "validated": mismatch is None,
        "agreement": agreement,
        "mismatch_type": mismatch,
        "voice": {"pre": voice_pre, "post": voice_post, "trend": round(voice_trend, 2)},
        "hrv": {"pre": hrv_pre, "post": hrv_post, "trend": round(hrv_trend, 2),
                "rmssd_pre": hrv_pre_rmssd, "rmssd_post": hrv_post_rmssd},
    }
