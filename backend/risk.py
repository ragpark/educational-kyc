from typing import Dict

STANDARD_SCORES = {
    "good": 1.0,
    "poor": 0.0,
    "unknown": 0.5,
}


def calculate_risk_score(data: Dict) -> float:
    """Calculate a 0-10 partnership risk score based on centre features."""
    years_operating = min(data.get("years_operating", 0), 20) / 20
    similar = 1.0 if data.get("offers_similar_courses") else 0.0
    standards = STANDARD_SCORES.get(
        str(data.get("standards_verification", "unknown")).lower(), 0.5
    )
    years_known = min(data.get("years_known_ao", 0), 20) / 20
    payment = 0.0 if data.get("late_payment_history") else 1.0

    score = (
        0.25 * years_operating
        + 0.15 * similar
        + 0.25 * standards
        + 0.20 * years_known
        + 0.15 * payment
    ) * 10
    return round(score, 2)


def classify_partner(score: float) -> str:
    if score >= 10:
        return "Strategic Partner"
    if score >= 7:
        return "Sector Partner"
    if score >= 3:
        return "Established Partner"
    return "Developing Partner"
