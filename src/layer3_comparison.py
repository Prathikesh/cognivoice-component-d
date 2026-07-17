"""Layer 3: pre/post meditation session comparison.

Pure logic, no ML. Compares the Layer 2 stress scores taken before and
after a session and reports whether the change is real or within noise.
"""

# score changes smaller than this (on the 0-10 scale) are treated as
# measurement noise, scaled up when the model was less confident
NOISE_FLOOR = 0.75
MIN_CONFIDENCE = 0.15


def _magnitude(delta_abs: float) -> str:
    if delta_abs < 1.5:
        return "slight"
    if delta_abs < 3.0:
        return "moderate"
    return "strong"


def compare_scores(pre: dict, post: dict) -> dict:
    """Compare two Layer 2 outputs.

    pre/post: {"stress_score": 0-10, "confidence": 0-1, ...}
    """
    delta = round(post["stress_score"] - pre["stress_score"], 2)
    mean_conf = (pre["confidence"] + post["confidence"]) / 2

    # low confidence widens the band of changes we refuse to interpret
    noise = NOISE_FLOOR * (2.0 - mean_conf)
    reliable = abs(delta) >= noise and mean_conf >= MIN_CONFIDENCE

    if not reliable:
        direction = "no_reliable_change"
    elif delta < 0:
        direction = "improved"
    else:
        direction = "worsened"

    return {
        "pre_stress": pre["stress_score"],
        "post_stress": post["stress_score"],
        "delta": delta,
        "direction": direction,
        "improved": reliable and delta < 0,
        "magnitude": _magnitude(abs(delta)) if reliable else "none",
        "reliable": reliable,
        "mean_confidence": round(mean_conf, 3),
    }
