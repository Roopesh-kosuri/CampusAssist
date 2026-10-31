"""Privacy and PII (Personally Identifiable Information) Redaction Module.

Safeguards student privacy by detecting and masking sensitive data (Indian mobile numbers,
LPU registration/roll numbers, and personal email addresses) before user queries are logged
to SQLite or processed by downstream components.
"""
import re

# Regex patterns for Indian student PII
# 1. Email pattern: user@domain.tld
EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
    re.IGNORECASE
)

# 2. Indian Mobile numbers: optional +91 or 0 prefix followed by 10 digits starting with 6, 7, 8, or 9
PHONE_PATTERN = re.compile(
    r"(?:\+91[\-\s]?|0)?[6-9]\d{4}[\-\s]?\d{5}\b"
)

# 3. LPU 8-digit Student Registration / UID Numbers (e.g., 12015843, 11804521)
REG_NO_PATTERN = re.compile(
    r"\b\d{8}\b"
)


def contains_pii(text: str) -> bool:
    """Check if the text contains any identifiable PII."""
    if not text:
        return False
    return bool(
        EMAIL_PATTERN.search(text)
        or PHONE_PATTERN.search(text)
        or REG_NO_PATTERN.search(text)
    )


def redact_pii(text: str) -> tuple[str, bool]:
    """Redact student PII from query text.

    Returns:
        tuple[str, bool]: (sanitized_text, was_redacted)
    """
    if not text:
        return text, False

    original_text = text
    # 1. Redact Emails
    redacted = EMAIL_PATTERN.sub("[REDACTED_EMAIL]", text)

    # 2. Redact Phone Numbers
    redacted = PHONE_PATTERN.sub("[REDACTED_PHONE]", redacted)

    # 3. Redact 8-digit Student Registration Numbers
    redacted = REG_NO_PATTERN.sub("[REDACTED_REG_NO]", redacted)

    was_redacted = redacted != original_text
    return redacted, was_redacted
