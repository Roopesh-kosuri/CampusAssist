"""Unit tests for Phase 5: Per-method threshold calibration and fallback routing."""
import json
import pytest
from src.config import THRESHOLDS_PATH, RESULTS_DIR
from src.fallback import FallbackRouter, DEFAULT_DEPARTMENT_CONTACTS, DEFAULT_THRESHOLDS


def test_thresholds_file_structure():
    assert THRESHOLDS_PATH.exists(), "results/thresholds.json does not exist"
    with open(THRESHOLDS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data.get("tuned_on") == "dev", "Thresholds must be tuned strictly on the dev split"
    thresholds = data.get("thresholds", {})
    required_methods = ["kw", "tf", "emb", "emb_kw", "hyb"]
    for m in required_methods:
        assert m in thresholds, f"Missing method {m} in thresholds.json"
        tau = thresholds[m]
        assert isinstance(tau, (int, float))
        assert 0.10 <= tau <= 0.95, f"Threshold {tau} out of realistic bounds [0.10, 0.95] for {m}"

    metrics = data.get("metrics", {})
    for m in required_methods:
        assert m in metrics
        assert "dev_coverage_pct" in metrics[m]
        assert "dev_precision_pct" in metrics[m]
        assert "dev_oos_rejection_pct" in metrics[m]


def test_score_distributions_file():
    dist_path = RESULTS_DIR / "score_distributions.json"
    assert dist_path.exists(), "results/score_distributions.json does not exist"
    with open(dist_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for m in ["kw", "tf", "emb", "emb_kw", "hyb"]:
        assert m in data
        assert "correct_matches" in data[m]
        assert "oos_queries" in data[m]
        # Check distribution statistics
        correct = data[m]["correct_matches"]
        oos = data[m]["oos_queries"]
        assert correct["count"] > 0
        assert oos["count"] > 0
        assert correct["mean"] >= oos["mean"], f"Expected correct matches mean >= OOS mean for {m}"


def test_fallback_router_logic():
    router = FallbackRouter()
    # Check default department contacts
    for cat in ["Hostel", "Library", "Fees", "ID Card", "Transport", "Exams", "All"]:
        contact = router.get_department_contact(cat)
        assert isinstance(contact, str) and len(contact) > 10

    # Check unknown category defaults to All
    assert router.get_department_contact("RandomNonExistentCategory") == router.get_department_contact("All")

    # Check fallback decision
    tau_hyb = router.get_threshold("hyb")
    assert router.should_fallback(tau_hyb - 0.05, "hyb") is True
    assert router.should_fallback(tau_hyb + 0.05, "hyb") is False

    # Check payload structure
    mock_candidates = [
        {"id": "hos_01", "question": "Fan repair", "answer": "Contact [warden]", "score": 0.25, "category": "Hostel"}
    ]
    payload = router.create_fallback_payload(
        query="Alien invasion help",
        method_code="hyb",
        category="Hostel",
        top_candidates=mock_candidates
    )

    assert payload["fallback"] is True
    assert payload["method"] == "hyb"
    assert payload["category"] == "Hostel"
    assert payload["confidence"] == 0.25
    assert payload["threshold"] == tau_hyb
    assert "Hostel Warden Helpdesk" in payload["department_contact"]
    assert payload["top3"] == mock_candidates
    assert payload["answer_original"] is None
