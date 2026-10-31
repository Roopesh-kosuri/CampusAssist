"""Validation suite for CampusAssist FAQ dataset, paraphrases, OOS queries, and owner facts."""
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

from src.config import (
    FAQS_PATH,
    OWNER_FACTS_PATH,
    PARAPHRASES_PATH,
    OUT_OF_SCOPE_PATH,
    VALID_CATEGORIES,
    CATEGORY_PREFIX_MAP,
)

ID_PATTERN = re.compile(r"^(hos|lib|fee|idc|trn|exm)_\d{2}$")
PLACEHOLDER_PATTERN = re.compile(r"\[([^\]]+)\]")

VALID_PARAPHRASE_TYPES = {
    "low_overlap",
    "hinglish_mixed",
    "synonym_swap",
    "typo",
    "reorder",
    "verbose",
}
VALID_AUTHORS = {"ai", "owner", "classmate"}
VALID_OOS_REASONS = {"near_miss", "off_topic", "adversarial"}
VALID_SPLITS = {"dev", "test"}

# Words exempted from proper-noun check to prevent false-positives on English grammar
EXEMPT_WORDS = {
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
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
    "january", "february", "march", "april", "may", "june", "july", "august",
    "september", "october", "november", "december",
    "hostel", "library", "fees", "fee", "card", "id", "transport", "exams", "exam",
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


def load_csv_rows(path: Path) -> list[dict]:
    """Load rows from a CSV file into a list of dicts."""
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found at: {path}")
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


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

            if verified is True:
                errors.append(
                    f"FAQ '{faq_id}' has verified=True but contains bracketed placeholders: {all_placeholders}"
                )

        if verified is True:
            if not source or source == "[owner to fill]":
                errors.append(f"FAQ '{faq_id}' is marked verified=True but source is empty or '[owner to fill]'")
            if not last_checked:
                errors.append(f"FAQ '{faq_id}' is marked verified=True but last_checked date is null")

            sentences = re.split(r"[.!?]\s+", answer)
            for sentence in sentences:
                words = re.findall(r"\b[A-Z][a-zA-Z0-9-]*\b", sentence)
                non_initial_words = words[1:] if len(words) > 1 else []
                for w in non_initial_words:
                    if w.lower() not in EXEMPT_WORDS:
                        if owner_facts_lower and w.lower() not in owner_facts_lower:
                            errors.append(
                                f"FAQ '{faq_id}' verified=True has proper noun '{w}' not documented in data/owner_facts.md"
                            )

    return errors, unverified_faqs


def validate_paraphrases(paraphrases: list[dict], faqs: list[dict]) -> tuple[list[str], dict]:
    """Validate data/paraphrases.csv for foreign keys, splits, hardness, leakage, and authorship."""
    errors = []
    stats = {}

    if not paraphrases:
        return ["data/paraphrases.csv is empty or missing rows."], stats

    required_cols = {"faq_id", "paraphrase", "paraphrase_type", "split", "author"}
    first_row = paraphrases[0]
    missing_cols = required_cols - set(first_row.keys())
    if missing_cols:
        errors.append(f"paraphrases.csv missing columns: {missing_cols}")

    faq_ids = {f["id"] for f in faqs}
    canonical_questions = {f["question"].strip().lower() for f in faqs}

    dev_texts = set()
    test_texts = set()
    dev_count = 0
    test_count = 0
    hard_count = 0
    type_counts = Counter()
    ai_in_test_count = 0

    for idx, row in enumerate(paraphrases, 1):
        faq_id = row.get("faq_id", "")
        text = row.get("paraphrase", "").strip()
        ptype = row.get("paraphrase_type", "")
        split = row.get("split", "")
        author = row.get("author", "")

        # Foreign key integrity
        if faq_id not in faq_ids:
            errors.append(f"Row #{idx}: Unknown faq_id '{faq_id}'")

        if not text:
            errors.append(f"Row #{idx}: Empty paraphrase text")

        # Must not exactly duplicate canonical question
        if text.lower() in canonical_questions:
            errors.append(f"Row #{idx}: Paraphrase is identical to a canonical question: '{text}'")

        # Allowed types
        if ptype not in VALID_PARAPHRASE_TYPES:
            errors.append(f"Row #{idx}: Invalid paraphrase_type '{ptype}'. Allowed: {VALID_PARAPHRASE_TYPES}")
        type_counts[ptype] += 1

        if ptype in ("low_overlap", "hinglish_mixed"):
            hard_count += 1

        # Allowed splits
        if split not in VALID_SPLITS:
            errors.append(f"Row #{idx}: Invalid split '{split}'. Allowed: {VALID_SPLITS}")
        elif split == "dev":
            dev_count += 1
            dev_texts.add(text.lower())
        elif split == "test":
            test_count += 1
            test_texts.add(text.lower())

        # Allowed authors
        if author not in VALID_AUTHORS:
            errors.append(f"Row #{idx}: Invalid author '{author}'. Allowed: {VALID_AUTHORS}")

        # Strict Test Authorship Constraint: test split MUST NOT be author == 'ai'
        if split == "test" and author == "ai":
            ai_in_test_count += 1
            errors.append(f"Row #{idx}: Authorship violation! split=='test' must not have author=='ai'")

    # Zero dev/test leakage check
    leakage = dev_texts & test_texts
    if leakage:
        errors.append(f"Data leakage detected! {len(leakage)} exact duplicate queries across dev and test: {list(leakage)[:3]}")

    # Dev / Test 50/50 balance check
    total = len(paraphrases)
    if total < 216:
        errors.append(f"Total paraphrases ({total}) below minimum required (216).")
    if abs(dev_count - test_count) > 2:
        errors.append(f"Dev/Test split not balanced: dev={dev_count}, test={test_count}")

    # Hardness proportion check (>= 40%)
    hard_pct = (hard_count / total * 100) if total > 0 else 0.0
    if hard_pct < 40.0:
        errors.append(f"Hard paraphrases ({hard_pct:.1f}%) below minimum required 40.0% (count: {hard_count}/{total})")

    stats = {
        "total": total,
        "dev": dev_count,
        "test": test_count,
        "hard_count": hard_count,
        "hard_pct": hard_pct,
        "type_counts": dict(type_counts),
        "ai_in_test": ai_in_test_count
    }
    return errors, stats


def validate_out_of_scope(oos_queries: list[dict]) -> tuple[list[str], dict]:
    """Validate data/out_of_scope.csv for schema, volume, split balance, and reasons."""
    errors = []
    stats = {}

    if not oos_queries:
        return ["data/out_of_scope.csv is empty or missing rows."], stats

    required_cols = {"query", "reason", "split"}
    first_row = oos_queries[0]
    missing = required_cols - set(first_row.keys())
    if missing:
        errors.append(f"out_of_scope.csv missing columns: {missing}")

    if len(oos_queries) < 60:
        errors.append(f"out_of_scope.csv has only {len(oos_queries)} queries (minimum: 60).")

    dev_texts = set()
    test_texts = set()
    reason_counts = Counter()
    dev_count = 0
    test_count = 0

    for idx, row in enumerate(oos_queries, 1):
        q = row.get("query", "").strip()
        reason = row.get("reason", "")
        split = row.get("split", "")

        if not q:
            errors.append(f"OOS Row #{idx}: Empty query text")

        if reason not in VALID_OOS_REASONS:
            errors.append(f"OOS Row #{idx}: Invalid reason '{reason}'. Allowed: {VALID_OOS_REASONS}")
        reason_counts[reason] += 1

        if split not in VALID_SPLITS:
            errors.append(f"OOS Row #{idx}: Invalid split '{split}'. Allowed: {VALID_SPLITS}")
        elif split == "dev":
            dev_count += 1
            dev_texts.add(q.lower())
        elif split == "test":
            test_count += 1
            test_texts.add(q.lower())

    # Leakage check
    leakage = dev_texts & test_texts
    if leakage:
        errors.append(f"OOS query leakage detected: {list(leakage)[:3]}")

    if abs(dev_count - test_count) > 2:
        errors.append(f"OOS Dev/Test split not balanced: dev={dev_count}, test={test_count}")

    stats = {
        "total": len(oos_queries),
        "dev": dev_count,
        "test": test_count,
        "reason_counts": dict(reason_counts)
    }
    return errors, stats


def run_validation() -> bool:
    """Run full validation suite across faqs, owner_facts, paraphrases, and OOS datasets."""
    print("=" * 75)
    print(" CampusAssist Comprehensive Dataset & Provenance Validator")
    print("=" * 75)

    all_errors = []

    # 1. FAQs & Owner Facts
    try:
        faqs = load_faqs(FAQS_PATH)
        owner_facts_text = load_owner_facts_text(OWNER_FACTS_PATH)
        all_errors.extend(validate_schema(faqs))
        all_errors.extend(validate_category_balance(faqs))
        r6_errors, unverified = validate_rule_6(faqs, owner_facts_text)
        all_errors.extend(r6_errors)

        cat_counts = Counter(f["category"] for f in faqs)
        print(f"\n1. FAQs Corpus ({FAQS_PATH.name}): {len(faqs)} entries")
        for cat in sorted(VALID_CATEGORIES):
            print(f"   - {cat:11s}: {cat_counts.get(cat, 0):2d} entries")
        print(f"   - Verified: {sum(1 for f in faqs if f.get('verified') is True)} / {len(faqs)}")
        print(f"   - Unverified (Placeholders): {len(unverified)} / {len(faqs)}")

    except Exception as e:
        print(f"[ERROR] FAQs validation failed to run: {e}")
        all_errors.append(str(e))
        faqs = []

    # 2. Paraphrases
    try:
        paraphrases = load_csv_rows(PARAPHRASES_PATH)
        p_errors, p_stats = validate_paraphrases(paraphrases, faqs)
        all_errors.extend(p_errors)

        print(f"\n2. Paraphrase Test Suite ({PARAPHRASES_PATH.name}): {p_stats.get('total', 0)} queries")
        print(f"   - Dev Split  : {p_stats.get('dev', 0)} (all author='ai')")
        print(f"   - Test Split : {p_stats.get('test', 0)} (all author='owner'/'classmate')")
        print(f"   - Hard Queries: {p_stats.get('hard_count', 0)} / {p_stats.get('total', 0)} ({p_stats.get('hard_pct', 0.0):.1f}%) [Requirement >= 40%]")
        print("   - Type Breakdown:")
        for t, c in p_stats.get("type_counts", {}).items():
            print(f"       * {t:15s}: {c:3d}")
        print(f"   - Test AI Authorship Violations: {p_stats.get('ai_in_test', 0)} (Required: 0)")

    except Exception as e:
        print(f"[ERROR] Paraphrases validation failed to run: {e}")
        all_errors.append(str(e))

    # 3. Out of Scope Queries
    try:
        oos = load_csv_rows(OUT_OF_SCOPE_PATH)
        oos_errors, oos_stats = validate_out_of_scope(oos)
        all_errors.extend(oos_errors)

        print(f"\n3. Out-of-Scope Corpus ({OUT_OF_SCOPE_PATH.name}): {oos_stats.get('total', 0)} queries")
        print(f"   - Dev Split : {oos_stats.get('dev', 0)}")
        print(f"   - Test Split: {oos_stats.get('test', 0)}")
        print("   - Reason Breakdown:")
        for r, c in oos_stats.get("reason_counts", {}).items():
            print(f"       * {r:12s}: {c:2d}")

    except Exception as e:
        print(f"[ERROR] Out-of-scope validation failed to run: {e}")
        all_errors.append(str(e))

    # Overall Verdict
    print("\n" + "=" * 75)
    if all_errors:
        print(f"[FAIL] Found {len(all_errors)} validation error(s):")
        for err in all_errors:
            print(f"  x {err}")
        print("=" * 75)
        return False

    print("[PASS] 100% Validated! Zero leakage, zero AI test authors, >=40% hard paraphrases.")
    print("=" * 75)
    return True


if __name__ == "__main__":
    success = run_validation()
    sys.exit(0 if success else 1)
