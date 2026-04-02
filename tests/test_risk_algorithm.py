from backend.risk import calculate_risk_score, classify_partner


def test_risk_scoring_and_classification():
    features = {
        "years_operating": 10,
        "offers_similar_courses": True,
        "standards_verification": "good",
        "years_known_ao": 8,
        "late_payment_history": False,
    }
    score = calculate_risk_score(features)
    assert score == 7.55
    assert classify_partner(score) == "Sector Partner"
