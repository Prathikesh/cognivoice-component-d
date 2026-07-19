"""Layer 4: cross-modal validation - voice stress vs HRV (Component B).

Two independent signals agreeing is far stronger evidence than either
alone. Rule-based by design: the agreement logic is explainable, and no
labelled dataset of voice-vs-HRV mismatches exists to train on.

Component boundary: Component B PRODUCES the HRV values (RMSSD); this
layer CONSUMES them. All cross-modal logic belongs to Component D.
"""


class HRVProvider:
    """Interface Component B implements. RMSSD in milliseconds."""

    def get_rmssd(self, session_id: str, phase: str) -> float | None:
        raise NotImplementedError


class StoredHRVProvider(HRVProvider):
    """Production provider: Component B pushes values through the API
    endpoint /session-update; this class stores and serves them."""

    def __init__(self):
        self.store: dict[tuple[str, str], float] = {}

    def push(self, session_id: str, phase: str, rmssd: float):
        self.store[(session_id, phase)] = rmssd

    def get_rmssd(self, session_id: str, phase: str) -> float | None:
        return self.store.get((session_id, phase))


class MockHRVProvider(HRVProvider):
    """Demo/test stand-in: mildly stressed before, recovered after."""

    def __init__(self, pre_rmssd: float = 35.0, post_rmssd: float = 55.0):
        self.values = {"pre": pre_rmssd, "post": post_rmssd}

    def get_rmssd(self, session_id: str, phase: str) -> float | None:
        return self.values.get(phase)


def hrv_stress_score(rmssd: float) -> float:
    """Map RMSSD to a 0-10 stress proxy. Physiology: LOWER heart-rate
    variability = MORE stressed. Typical adult resting range spans
    roughly 20 ms (stressed) to 80 ms (relaxed)."""
    score01 = (80.0 - rmssd) / 60.0
    return round(min(1.0, max(0.0, score01)) * 10, 2)


# Voice and HRV stress levels within this distance (0-10 scale) agree.
LEVEL_TOLERANCE = 3.0


def validate_crossmodal(voice_pre: float, voice_post: float,
                        hrv_pre_rmssd: float, hrv_post_rmssd: float) -> dict:
    """Compare the two signals at both time points AND their trends,
    and classify any disagreement into one of four named types."""
    hrv_pre = hrv_stress_score(hrv_pre_rmssd)
    hrv_post = hrv_stress_score(hrv_post_rmssd)

    voice_trend = voice_post - voice_pre
    hrv_trend = hrv_post - hrv_pre
    # Trends agree if both move the same direction, or both are ~flat.
    trends_agree = (voice_trend * hrv_trend > 0) or \
                   (abs(voice_trend) < 1.0 and abs(hrv_trend) < 1.0)

    pre_agree = abs(voice_pre - hrv_pre) <= LEVEL_TOLERANCE
    post_agree = abs(voice_post - hrv_post) <= LEVEL_TOLERANCE

    # Mismatch typing. Trend disagreement is classified FIRST because it
    # carries the most meaning (direction of change), then level gaps.
    mismatch = None
    if not trends_agree:
        if voice_trend < hrv_trend:
            mismatch = "vocal_masking"          # voice calmer than body
        else:
            mismatch = "cognitive_persistence"  # body recovered, voice not
    elif not pre_agree and not post_agree:
        mismatch = "baseline_divergence"        # signals disagree throughout
    elif not post_agree:
        mismatch = "outcome_divergence"         # agreed before, not after
    elif not pre_agree:
        mismatch = "baseline_divergence"

    # Agreement score in [0,1]: mean closeness across both time points.
    closeness = 1.0 - (abs(voice_pre - hrv_pre) + abs(voice_post - hrv_post)) / 20.0
    agreement = round(max(0.0, closeness), 3)

    return {
        "validated": mismatch is None,
        "agreement": agreement,
        "mismatch_type": mismatch,
        "voice": {"pre": voice_pre, "post": voice_post,
                  "trend": round(voice_trend, 2)},
        "hrv": {"pre": hrv_pre, "post": hrv_post,
                "trend": round(hrv_trend, 2),
                "rmssd_pre": hrv_pre_rmssd, "rmssd_post": hrv_post_rmssd},
    }
