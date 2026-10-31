"""AST and Regex-based Grounding Verification Module.

Enforces zero-hallucination guarantees by comparing the original FAQ answer
with the LLM-polished text before returning it to the student. If the LLM
introduces any new numeric token, email address, URL, or alters/omits any
[bracketed placeholder], grounding verification fails immediately.
"""
import re

# Regex extractors
PLACEHOLDER_PATTERN = re.compile(r"\[.*?\]")
NUMERIC_PATTERN = re.compile(r"\b\d+(?:\.\d+)?\b")
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", re.IGNORECASE)
URL_PATTERN = re.compile(r"https?://[^\s]+|www\.[^\s]+", re.IGNORECASE)


def extract_entities(text: str) -> dict:
    """Extract placeholders, numbers, emails, and URLs from text."""
    if not text:
        return {
            "placeholders": set(),
            "numbers": set(),
            "emails": set(),
            "urls": set()
        }

    # Extract bracketed placeholders
    placeholders = set(PLACEHOLDER_PATTERN.findall(text))

    # Mask placeholders before extracting numbers so numbers inside valid placeholders don't conflict
    masked_text = text
    for p in placeholders:
        masked_text = masked_text.replace(p, " ")

    numbers = set(NUMERIC_PATTERN.findall(masked_text))
    emails = set(EMAIL_PATTERN.findall(text))
    urls = set(URL_PATTERN.findall(text))

    return {
        "placeholders": placeholders,
        "numbers": numbers,
        "emails": emails,
        "urls": urls
    }


def verify_grounding(original_text: str, polished_text: str) -> tuple[bool, str, dict]:
    """Verify that polished_text is strictly grounded in original_text.

    Returns:
        tuple[bool, str, dict]: (grounding_passed, reason, details)
    """
    if not polished_text or not polished_text.strip():
        return False, "Polished text is empty", {}

    orig = extract_entities(original_text)
    pol = extract_entities(polished_text)

    details = {
        "orig_placeholders": list(orig["placeholders"]),
        "pol_placeholders": list(pol["placeholders"]),
        "orig_numbers": list(orig["numbers"]),
        "pol_numbers": list(pol["numbers"]),
        "orig_emails": list(orig["emails"]),
        "pol_emails": list(pol["emails"]),
        "orig_urls": list(orig["urls"]),
        "pol_urls": list(pol["urls"]),
    }

    # 1. Bracketed Placeholders Verification: Must preserve every placeholder verbatim
    missing_placeholders = orig["placeholders"] - pol["placeholders"]
    if missing_placeholders:
        reason = f"Omitted or altered [bracketed placeholder](s): {sorted(missing_placeholders)}"
        return False, reason, details

    new_placeholders = pol["placeholders"] - orig["placeholders"]
    if new_placeholders:
        reason = f"Introduced unverified placeholder(s): {sorted(new_placeholders)}"
        return False, reason, details

    # 2. Numeric Hallucination Check: No new numbers allowed
    new_numbers = pol["numbers"] - orig["numbers"]
    if new_numbers:
        reason = f"Hallucinated numeric tokens: {sorted(new_numbers)}"
        return False, reason, details

    # 3. Email Hallucination Check: No new emails allowed
    new_emails = pol["emails"] - orig["emails"]
    if new_emails:
        reason = f"Hallucinated email address(es): {sorted(new_emails)}"
        return False, reason, details

    # 4. URL Hallucination Check: No new URLs allowed
    new_urls = pol["urls"] - orig["urls"]
    if new_urls:
        reason = f"Hallucinated URL(s): {sorted(new_urls)}"
        return False, reason, details

    return True, "Grounding verification passed", details
