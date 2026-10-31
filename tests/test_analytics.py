"""Unit tests for src/analytics.py (SQLite Telemetry)."""
import pytest
from src.analytics import init_db, log_query, record_feedback, get_analytics


@pytest.fixture
def temp_db(tmp_path):
    return tmp_path / "test_query_logs.db"


def test_init_db(temp_db):
    init_db(temp_db)
    assert temp_db.exists()
    analytics = get_analytics(temp_db)
    assert analytics["total_queries"] == 0
    assert analytics["fallback_rate"] == 0.0


def test_log_query_and_feedback(temp_db):
    qid = log_query(
        query="When does library close?",
        method="hyb",
        category_filter="Library",
        matched_faq_id="lib_01",
        score=0.88,
        threshold_used=0.40,
        fallback=False,
        polished=False,
        groq_latency_ms=None,
        groq_failed=False,
        latency_ms=8.5,
        db_path=temp_db
    )
    assert qid == 1

    # Record feedback
    ok = record_feedback(qid, helpful=True, db_path=temp_db)
    assert ok is True

    # Check analytics
    analytics = get_analytics(temp_db)
    assert analytics["total_queries"] == 1
    assert analytics["fallback_rate"] == 0.0
    assert analytics["avg_confidence"] == 88.0
    assert analytics["helpful_percent"] == 100.0
    assert analytics["by_category"]["Library"] == 1


def test_log_fallback_query(temp_db):
    qid = log_query(
        query="Alien invasion help",
        method="hyb",
        category_filter="All",
        matched_faq_id=None,
        score=0.15,
        threshold_used=0.40,
        fallback=True,
        polished=False,
        groq_latency_ms=None,
        groq_failed=False,
        latency_ms=5.2,
        db_path=temp_db
    )
    assert qid == 1

    analytics = get_analytics(temp_db)
    assert analytics["total_queries"] == 1
    assert analytics["fallback_rate"] == 100.0
    assert "Alien invasion help" in analytics["recent_fallbacks"]
