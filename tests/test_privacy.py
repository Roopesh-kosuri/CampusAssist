"""Unit tests for src/privacy.py (PII Redaction)."""
import pytest
from src.privacy import redact_pii, contains_pii


def test_no_pii():
    text = "Where is the central library located and what are the closing times?"
    redacted, was_redacted = redact_pii(text)
    assert not was_redacted
    assert redacted == text
    assert not contains_pii(text)


def test_redact_email():
    text = "My name is Aman and my email is aman.123@gmail.com please send my admit card"
    redacted, was_redacted = redact_pii(text)
    assert was_redacted
    assert "[REDACTED_EMAIL]" in redacted
    assert "aman.123@gmail.com" not in redacted


def test_redact_phone():
    cases = [
        ("Call me at +91 9876543210 regarding hostel fee", "+91 9876543210"),
        ("My number is +91-9876543210 for verification", "+91-9876543210"),
        ("Reach out at 9876543210", "9876543210"),
        ("Call 08765432109 tomorrow", "08765432109")
    ]
    for text, raw_num in cases:
        redacted, was_redacted = redact_pii(text)
        assert was_redacted, f"Failed to detect phone in {text}"
        assert "[REDACTED_PHONE]" in redacted
        assert raw_num not in redacted


def test_redact_registration_number():
    text = "My LPU registration number is 12015843 and I lost my ID card"
    redacted, was_redacted = redact_pii(text)
    assert was_redacted
    assert "[REDACTED_REG_NO]" in redacted
    assert "12015843" not in redacted


def test_combined_pii():
    text = "Student 11902485 phone +91 9812345678 email rohit@lpu.in needs fee receipt"
    redacted, was_redacted = redact_pii(text)
    assert was_redacted
    assert "[REDACTED_REG_NO]" in redacted
    assert "[REDACTED_PHONE]" in redacted
    assert "[REDACTED_EMAIL]" in redacted
    assert "11902485" not in redacted
    assert "9812345678" not in redacted
    assert "rohit@lpu.in" not in redacted
