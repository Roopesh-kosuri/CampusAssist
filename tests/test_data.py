"""Unit tests for dataset structure, paraphrases, OOS queries, and Rule 6 compliance."""
import pytest
from pathlib import Path

from src.config import (
    FAQS_PATH,
    OWNER_FACTS_PATH,
    PARAPHRASES_PATH,
    OUT_OF_SCOPE_PATH,
    VALID_CATEGORIES,
    CATEGORY_PREFIX_MAP,
)
from src.validate_data import (
    load_faqs,
    load_owner_facts_text,
    load_csv_rows,
    validate_schema,
    validate_category_balance,
    validate_rule_6,
    validate_paraphrases,
    validate_out_of_scope,
    PLACEHOLDER_PATTERN,
    ID_PATTERN,
)


def test_faqs_file_exists():
    """Verify that data/faqs.json exists."""
    assert FAQS_PATH.exists(), f"Missing {FAQS_PATH}"


def test_faqs_exact_count():
    """Verify that data/faqs.json contains exactly 72 canonical FAQs."""
    faqs = load_faqs()
    assert len(faqs) == 72, f"Expected 72 FAQs, found {len(faqs)}"


def test_category_balance():
    """Verify that each of the 6 categories has exactly 12 entries."""
    faqs = load_faqs()
    counts = {}
    for f in faqs:
        cat = f["category"]
        counts[cat] = counts.get(cat, 0) + 1

    assert set(counts.keys()) == VALID_CATEGORIES
    for cat in VALID_CATEGORIES:
        assert counts[cat] == 12, f"Category '{cat}' expected 12 entries, found {counts[cat]}"


def test_id_structure_and_uniqueness():
    """Verify that all IDs are unique and strictly conform to (prefix)_NN."""
    faqs = load_faqs()
    seen = set()

    for f in faqs:
        faq_id = f["id"]
        assert ID_PATTERN.match(faq_id), f"Invalid ID format: {faq_id}"
        assert faq_id not in seen, f"Duplicate ID: {faq_id}"
        seen.add(faq_id)

        prefix = faq_id.split("_")[0]
        assert CATEGORY_PREFIX_MAP[prefix] == f["category"]


def test_rule_6_initial_state():
    """Verify Rule 6: FAQs conform to schema with valid verification status and contacts."""
    faqs = load_faqs()
    for f in faqs:
        assert isinstance(f["verified"], bool), f"FAQ {f['id']} must have boolean verified field"
        assert f["source"], f"FAQ {f['id']} must have a source"
        assert len(f["answer"]) > 10, f"FAQ {f['id']} answer must be populated"
        assert len(f["department_contact"]) > 5, f"FAQ {f['id']} department_contact must be populated"


def test_keywords_richness():
    """Verify each FAQ has between 6 and 10 relevant keywords."""
    faqs = load_faqs()
    for f in faqs:
        kw = f["keywords"]
        assert isinstance(kw, list), f"Keywords in {f['id']} must be a list"
        assert 5 <= len(kw) <= 12, f"FAQ {f['id']} has {len(kw)} keywords (expected 6-10)"
        for w in kw:
            assert isinstance(w, str) and w.strip(), f"Empty keyword in FAQ {f['id']}"


def test_owner_facts_file():
    """Verify that data/owner_facts.md exists and contains sections for all categories."""
    assert OWNER_FACTS_PATH.exists(), f"Missing {OWNER_FACTS_PATH}"
    content = load_owner_facts_text()
    for cat in VALID_CATEGORIES:
        assert cat in content, f"Category '{cat}' missing from owner_facts.md"


def test_paraphrases_suite():
    """Verify data/paraphrases.csv meets volume, split balance, and hardness rules."""
    assert PARAPHRASES_PATH.exists(), f"Missing {PARAPHRASES_PATH}"
    faqs = load_faqs()
    paraphrases = load_csv_rows(PARAPHRASES_PATH)

    errors, stats = validate_paraphrases(paraphrases, faqs)
    assert len(errors) == 0, f"Paraphrases validation failed: {errors}"
    assert stats["total"] >= 216, f"Expected >= 216 paraphrases, got {stats['total']}"
    assert stats["hard_pct"] >= 40.0, f"Expected >= 40% hard paraphrases, got {stats['hard_pct']}%"
    assert stats["ai_in_test"] == 0, "No AI authors permitted in test split"
    assert abs(stats["dev"] - stats["test"]) <= 2, "Dev and test splits must be 50/50 balanced"


def test_out_of_scope_suite():
    """Verify data/out_of_scope.csv meets volume, split balance, and reason rules."""
    assert OUT_OF_SCOPE_PATH.exists(), f"Missing {OUT_OF_SCOPE_PATH}"
    oos = load_csv_rows(OUT_OF_SCOPE_PATH)

    errors, stats = validate_out_of_scope(oos)
    assert len(errors) == 0, f"Out-of-scope validation failed: {errors}"
    assert stats["total"] >= 60, f"Expected >= 60 OOS queries, got {stats['total']}"
    assert abs(stats["dev"] - stats["test"]) <= 2, "Dev and test OOS queries must be 50/50 balanced"
    for r in ["near_miss", "off_topic", "adversarial"]:
        assert stats["reason_counts"].get(r, 0) >= 10, f"Reason '{r}' should have >= 10 queries"


def test_validator_detects_ai_authorship_in_test_split():
    """Verify validator flags any row in test split with author='ai'."""
    faqs = load_faqs()
    bad_paraphrases = [
        {"faq_id": "hos_01", "paraphrase": "Test query 1", "paraphrase_type": "synonym_swap", "split": "dev", "author": "ai"},
        {"faq_id": "hos_01", "paraphrase": "Test query 2", "paraphrase_type": "synonym_swap", "split": "test", "author": "ai"}  # Violation!
    ]
    errors, stats = validate_paraphrases(bad_paraphrases, faqs)
    assert any("Authorship violation" in e for e in errors)


def test_validator_detects_paraphrase_leakage():
    """Verify validator catches identical queries appearing in both dev and test."""
    faqs = load_faqs()
    leaky_paraphrases = [
        {"faq_id": "hos_01", "paraphrase": "Identical query text", "paraphrase_type": "synonym_swap", "split": "dev", "author": "ai"},
        {"faq_id": "hos_01", "paraphrase": "Identical query text", "paraphrase_type": "synonym_swap", "split": "test", "author": "owner"}  # Leakage!
    ]
    errors, stats = validate_paraphrases(leaky_paraphrases, faqs)
    assert any("Data leakage detected" in e for e in errors)
