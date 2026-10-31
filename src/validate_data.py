"""Validation suite for CampusAssist FAQ dataset and owner facts."""
import json
import re
import sys
from collections import Counter
from pathlib import Path

from src.config import FAQS_PATH, OWNER_FACTS_PATH, VALID_CATEGORIES, CATEGORY_PREFIX_MAP

ID_PATTERN = re.compile(r"^(hos|lib|fee|idc|trn|exm)_\d{2}$")
PLACEHOLDER_PATTERN = re.compile(r"\[([^\]]+)\]")

# Words exempted from proper-noun check to prevent false-positives on English grammar
EXEMPT_WORDS = {
    # Sentence starters and standard English words
    "the", "a", "an", "in", "on", "at", "for", "to", "from", "by", "with", "if",
    "when", "where", "how", "what", "why", "raise", "submit", "students", "student",
    "visit", "contact", "please", "check", "you", "your", "pay", "report", "carry",
    "apply", "download", "keep", "note", "return", "complete", "present", "bring",
    "connect", "access", "undergraduate", "postgraduate", "during", "offline", "online",
    "after", "before", "all", "each", "every", "high", "low", "special", "designated",
    "eligible", "failure", "failed", "call", "beyond", "multiple", "both", "either",
    "neither", "yes", "no", "new", "old", "first", "second", "third", "final",
    "central", "official", "general", "regular", "registered", "required", "prior",
    "only", "late", "open", "clear", "any", "this", "these", "such",
    # Days and Months
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
    "january", "february", "march", "april", "may", "june", "july", "august",
    "september", "october", "november", "december",
    # Categories
    "hostel", "library", "fees", "fee", "card", "id", "transport", "exams", "exam",
    # Common Campus / Tech Acronyms
    "uid", "rfid", "sms", "mac", "vpn", "opac", "ieee", "cgpa", "tgpa", "mte",
    "ete", "ca", "umc", "rms", "ums", "dsw", "dsa", "coe", "hr", "upi", "rupay",
    "pnb", "ugc", "aicte"
}


def load_faqs(path: Path = FAQS_PATH) -> list[dict]:
    """Load and parse the FAQs JSON file."""
    if not path.exists():
        raise FileNotFoundError(f"FAQ file not found at: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_owner_facts_text(path: Path = OWNER_FACTS_PATH) -> str:
    """Load text of owner facts markdown ledger if it exists."""
    if not path.exists():
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def validate_schema(faqs: list[dict]) -> list[str]:
    """Validate JSON structure, field presence, types, and ID format."""
    errors = []
    required_keys = {
        "id", "category", "question", "answer", "keywords",
        "department_contact", "verified", "source", "last_checked"
    }
    seen_ids = set()

    for idx, faq in enumerate(faqs):
        if not isinstance(faq, dict):
            errors.append(f"FAQ #{idx} is not a dictionary.")
            continue

        missing = required_keys - set(faq.keys())
        if missing:
            errors.append(f"FAQ #{idx} (ID: {faq.get('id', 'unknown')}) missing keys: {missing}")

        faq_id = faq.get("id", "")
        if not isinstance(faq_id, str) or not ID_PATTERN.match(faq_id):
            errors.append(f"FAQ #{idx} has invalid ID format '{faq_id}'. Expected pattern: (hos|lib|fee|idc|trn|exm)_NN")
        elif faq_id in seen_ids:
            errors.append(f"Duplicate FAQ ID '{faq_id}' at index {idx}.")
        else:
            seen_ids.add(faq_id)

        category = faq.get("category", "")
        if category not in VALID_CATEGORIES:
            errors.append(f"FAQ '{faq_id}' has invalid category '{category}'. Allowed: {VALID_CATEGORIES}")
        else:
            prefix = faq_id.split("_")[0] if "_" in faq_id else ""
            expected_cat = CATEGORY_PREFIX_MAP.get(prefix)
            if expected_cat and expected_cat != category:
                errors.append(f"FAQ '{faq_id}' prefix '{prefix}' does not match category '{category}' (expected '{expected_cat}')")

        for text_field in ("question", "answer", "department_contact"):
            val = faq.get(text_field)
            if not isinstance(val, str) or not val.strip():
                errors.append(f"FAQ '{faq_id}' has empty or non-string '{text_field}'")

        keywords = faq.get("keywords")
        if not isinstance(keywords, list) or len(keywords) < 5:
            errors.append(f"FAQ '{faq_id}' must have at least 5 keywords, got {len(keywords) if isinstance(keywords, list) else 'non-list'}")

    return errors


def validate_category_balance(faqs: list[dict], min_per_cat: int = 10) -> list[str]:
    """Validate that all 6 categories have sufficient questions."""
    errors = []
    cat_counts = Counter(f.get("category") for f in faqs if isinstance(f, dict))
    
    for cat in VALID_CATEGORIES:
        count = cat_counts.get(cat, 0)
        if count < min_per_cat:
            errors.append(f"Category '{cat}' has only {count} FAQs (minimum required: {min_per_cat}).")

    return errors


def validate_rule_6(faqs: list[dict], owner_facts_text: str = "") -> tuple[list[str], list[dict]]:
    """Validate Rule 6: placeholders and verified status rules."""
    errors = []
    unverified_faqs = []
    owner_facts_lower = owner_facts_text.lower()

    for faq in faqs:
        faq_id = faq.get("id", "unknown")
        answer = faq.get("answer", "")
        dept = faq.get("department_contact", "")
        verified = faq.get("verified", False)
        source = faq.get("source", "")
        last_checked = faq.get("last_checked")

        ans_placeholders = PLACEHOLDER_PATTERN.findall(answer)
        dept_placeholders = PLACEHOLDER_PATTERN.findall(dept)
        all_placeholders = ans_placeholders + dept_placeholders

        if all_placeholders:
            unverified_faqs.append({
                "id": faq_id,
                "category": faq.get("category"),
                "question": faq.get("question"),
                "placeholders": all_placeholders
            })

            # If it has bracketed placeholders, it MUST have verified: false
            if verified is True:
                errors.append(
                    f"FAQ '{faq_id}' has verified=True but contains bracketed placeholders: {all_placeholders}"
                )

        if verified is True:
            # Verified entries must have non-empty source and last_checked
            if not source or source == "[owner to fill]":
                errors.append(f"FAQ '{faq_id}' is marked verified=True but source is empty or '[owner to fill]'")
            if not last_checked:
                errors.append(f"FAQ '{faq_id}' is marked verified=True but last_checked date is null")

            # Check that capitalized proper nouns in answer appear in owner_facts.md
            # Ignore sentence starters and exempt words
            sentences = re.split(r"[.!?]\s+", answer)
            for sentence in sentences:
                words = re.findall(r"\b[A-Z][a-zA-Z0-9-]*\b", sentence)
                # First word in sentence is often capitalized, exempt it
                non_initial_words = words[1:] if len(words) > 1 else []
                for w in non_initial_words:
                    if w.lower() not in EXEMPT_WORDS:
                        if owner_facts_lower and w.lower() not in owner_facts_lower:
                            errors.append(
                                f"FAQ '{faq_id}' verified=True has proper noun '{w}' not documented in data/owner_facts.md"
                            )

    return errors, unverified_faqs


def run_validation(path: Path = FAQS_PATH, owner_facts_path: Path = OWNER_FACTS_PATH) -> bool:
    """Run full validation suite and print report."""
    print("=" * 70)
    print(" CampusAssist Dataset & Provenance Validator")
    print("=" * 70)

    try:
        faqs = load_faqs(path)
    except Exception as e:
        print(f"[ERROR] Failed to load FAQs: {e}")
        return False

    owner_facts_text = load_owner_facts_text(owner_facts_path)

    schema_errors = validate_schema(faqs)
    balance_errors = validate_category_balance(faqs)
    rule6_errors, unverified = validate_rule_6(faqs, owner_facts_text)

    all_errors = schema_errors + balance_errors + rule6_errors

    # Print summary statistics
    cat_counts = Counter(f["category"] for f in faqs)
    print(f"\nTotal FAQs Loaded: {len(faqs)}")
    print("Breakdown by Category:")
    for cat in sorted(VALID_CATEGORIES):
        print(f"  - {cat:12s}: {cat_counts.get(cat, 0):2d} entries")

    verified_count = sum(1 for f in faqs if f.get("verified") is True)
    unverified_count = len(faqs) - verified_count
    print(f"\nVerification Status:")
    print(f"  - Verified Entries  : {verified_count:2d} / {len(faqs)}")
    print(f"  - Unverified Entries: {unverified_count:2d} / {len(faqs)}")

    if unverified:
        print(f"\nVerification Checklist ({len(unverified)} entries awaiting Owner facts in data/owner_facts.md):")
        for u in unverified[:6]:  # preview first 6
            print(f"  [{u['id']}] ({u['category']}) {u['question'][:45]}... -> {len(u['placeholders'])} placeholders")
        if len(unverified) > 6:
            print(f"  ... and {len(unverified) - 6} more entries listed in data/owner_facts.md")

    if all_errors:
        print(f"\n[FAIL] Validation found {len(all_errors)} error(s):")
        for err in all_errors:
            print(f"  x {err}")
        print("=" * 70)
        return False

    print("\n[PASS] 0 schema errors! Category balance, placeholder rules, and integrity verified.")
    print("=" * 70)
    return True


if __name__ == "__main__":
    success = run_validation()
    sys.exit(0 if success else 1)
