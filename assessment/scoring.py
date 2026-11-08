BANDS = {"LOW": (0, 34), "MEDIUM": (35, 65), "HIGH": (66, 100)}
BEHAVIORAL_RANGES = {"LOW": (6, 13), "MEDIUM": (14, 22), "HIGH": (23, 29)}
ORDER = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}


def level_from_behavioral_score(score):
    if score <= 13:
        return "LOW"
    if score <= 22:
        return "MEDIUM"
    return "HIGH"


def compute_risk_score(final_level, behavioral_score):
    lo, hi = BANDS[final_level]
    if ORDER[final_level] < ORDER[level_from_behavioral_score(behavioral_score)]:
        t = 0.0
    else:
        b_lo, b_hi = BEHAVIORAL_RANGES[final_level]
        t = min(max((behavioral_score - b_lo) / (b_hi - b_lo), 0.0), 1.0)
    return round(lo + t * (hi - lo))


def profile_for_score(score):
    for level, (lo, hi) in BANDS.items():
        if lo <= score <= hi:
            return level
    raise ValueError(score)


def risk_title(score):
    return {"LOW": "محافظه‌کار", "MEDIUM": "متعادل", "HIGH": "تهاجمی"}[profile_for_score(score)]