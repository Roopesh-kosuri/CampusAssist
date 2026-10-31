"""Unit tests for FAQ dataset structure, category balance, and Rule 6 compliance."""
import pytest
from pathlib import Path

from src.config import FAQS_PATH, OWNER_FACTS_PATH, VALID_CATEGORIES, CATEGORY_PREFIX_MAP
from src.validate_data import (
    load_faqs,
    load_owner_facts_text,
    validate_schema,
    validate_category_balance,
    validate_rule_6,
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

        # Verify prefix matches category
        prefix = faq_id.split("_")[0]
        assert CATEGORY_PREFIX_MAP[prefix] == f["category"]


def test_rule_6_initial_state():
    """Verify Rule 6: all entries start unverified with bracketed placeholders."""
    faqs = load_faqs()
    for f in faqs:
        assert f["verified"] is False, f"FAQ {f['id']} must start with verified=False"
        assert f["source"] == "[owner to fill]", f"FAQ {f['id']} must start with source='[owner to fill]'"
        assert f["last_checked"] is None, f"FAQ {f['id']} must start with last_checked=None"

        # Check placeholders in answer and department contact
        ans_placeholders = PLACEHOLDER_PATTERN.findall(f["answer"])
        dept_placeholders = PLACEHOLDER_PATTERN.findall(f["department_contact"])
        assert len(ans_placeholders) >= 1, f"FAQ {f['id']} must have bracketed placeholders in answer"
        assert len(dept_placeholders) >= 1, f"FAQ {f['id']} must have bracketed placeholder in department_contact"


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


def test_validator_detects_schema_errors():
    """Verify that validator catches schema anomalies."""
    invalid_data = [
        {"id": "bad_id", "category": "Hostel", "question": "Q", "answer": "A", "keywords": ["a", "b"]},
        {"id": "hos_01", "category": "Unknown", "question": "", "answer": "A", "keywords": []},
    ]
    errors = validate_schema(invalid_data)
    assert len(errors) >= 3


def test_validator_detects_rule_6_violation():
    """Verify that validator flags an entry if verified=True while containing placeholders."""
    invalid_data = [
        {
            "id": "hos_01",
            "category": "Hostel",
            "question": "Sample Question?",
            "answer": "This has a [placeholder] here.",
            "department_contact": "[contact]",
            "verified": True,  # Violation!
            "source": "LPU Circular 12",
            "last_checked": "2026-10-31"
        }
    ]
    errors, _ = validate_rule_6(invalid_data)
    assert any("contains bracketed placeholders" in e for e in errors)


def test_validator_false_positive_guard_on_grammar():
    """Verify that sentence-initial capital words like 'Submit', 'Please', 'Check' do not trigger false positive errors."""
    valid_verified = [
        {
            "id": "lib_01",
            "category": "Library",
            "question": "What time does it close?",
            "answer": "Submit your books before closing. Please check with the desk on Sunday.",
            "department_contact": "Central Library Desk",
            "verified": True,
            "source": "LPU Library Circular 2026",
            "last_checked": "2026-10-31"
        }
    ]
    errors, _ = validate_rule_6(valid_verified, owner_facts_text="Central Library Desk")
    assert len(errors) == 0, f"False positive triggered: {errors}"
