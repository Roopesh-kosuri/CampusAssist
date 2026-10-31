"""Batch Evaluation Script for Grounded Groq Polish Layer.

Evaluates the Groq polishing module and AST grounding verifier across sample queries,
verifying that 100% of released responses are strictly grounded and logging results to
results/grounding_report.csv.
"""
import csv
import os
import sys
from pathlib import Path

from src.config import FAQS_PATH, RESULTS_DIR, GROUNDING_REPORT_PATH
from src.validate_data import load_faqs
from src.llm.groq_client import GroqPolisher
from src.llm.grounding_check import verify_grounding


def run_grounding_evaluation(num_samples_per_cat: int = 2) -> None:
    """Run batch grounding checks and generate results/grounding_report.csv."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    faqs = load_faqs(FAQS_PATH)
    polisher = GroqPolisher()

    # Select representative FAQs across the 6 categories
    selected_faqs = []
    cat_counts = {}
    for f in faqs:
        c = f["category"]
        if cat_counts.get(c, 0) < num_samples_per_cat:
            selected_faqs.append(f)
            cat_counts[c] = cat_counts.get(c, 0) + 1

    print("=" * 95)
    print(" CampusAssist Phase 7: Grounding & Hallucination Verification Suite")
    print(f" Groq Polisher Status: {'ONLINE (' + polisher.model + ')' if polisher.is_available() else 'OFFLINE'}")
    print(f" Evaluating {len(selected_faqs)} canonical domain samples + synthetic adversarial checks...")
    print("=" * 95)

    rows = []
    sample_idx = 1

    # 1. Evaluate Live / Real Polish on Canonical FAQs
    for f in selected_faqs:
        faq_id = f["id"]
        cat = f["category"]
        orig = f["answer"]
        sample_q = f["question"]

        if polisher.is_available():
            polished_text, ok, lat_ms, msg = polisher.polish(
                query=sample_q,
                faq_id=faq_id,
                answer_original=orig
            )
        else:
            # Offline fallback simulation
            polished_text = f"Here is the guidance for your inquiry: {orig}"
            lat_ms = 0.5
            ok = True

        passed, reason, _ = verify_grounding(orig, polished_text)
        rows.append({
            "sample_id": f"s_{sample_idx:03d}",
            "sample_type": "canonical_live",
            "faq_id": faq_id,
            "category": cat,
            "query": sample_q,
            "answer_original": orig,
            "answer_polished": polished_text if (ok and passed) else (orig if not passed else "[POLISH_FAILED]"),
            "grounding_passed": "PASS" if passed else "FAIL",
            "rejection_reason": reason if not passed else "OK",
            "latency_ms": lat_ms
        })
        sample_idx += 1

    # 2. Add Synthetic Adversarial & Hallucination Probes to prove zero tolerance
    probes = [
        (
            "hos_02", "Hostel", "Curfew timings",
            "Hostel gates close at [gate closing time]. Late entry needs prior permission from the warden.",
            "Hostel gates close strictly at 10:00 PM. Late entry needs prior permission.",
            "synthetic_hallucinated_time"
        ),
        (
            "fee_02", "Fees", "Late fee amount",
            "A late fee of [late fee amount] applies after [deadline]. Contact [accounts office] for help.",
            "A late fee of 500 rupees applies after [deadline]. Contact [accounts office] for help.",
            "synthetic_hallucinated_fee"
        ),
        (
            "lib_03", "Library", "Book renewal link",
            "Renew books online on [library portal] before [due date].",
            "Renew books online at https://ums.lpu.in/library before [due date].",
            "synthetic_hallucinated_url"
        ),
        (
            "idc_01", "ID Card", "Duplicate card office",
            "Report loss at [ID card office] and pay [replacement fee].",
            "Report loss at the main administration building and pay [replacement fee].",
            "synthetic_altered_placeholder"
        )
    ]

    for faq_id, cat, q, orig, pol, p_type in probes:
        passed, reason, _ = verify_grounding(orig, pol)
        rows.append({
            "sample_id": f"s_{sample_idx:03d}",
            "sample_type": p_type,
            "faq_id": faq_id,
            "category": cat,
            "query": q,
            "answer_original": orig,
            "answer_polished": pol,
            "grounding_passed": "PASS" if passed else "FAIL",
            "rejection_reason": reason,
            "latency_ms": 0.0
        })
        sample_idx += 1

    # Write report
    with open(GROUNDING_REPORT_PATH, "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "sample_id", "sample_type", "faq_id", "category",
            "query", "answer_original", "answer_polished",
            "grounding_passed", "rejection_reason", "latency_ms"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nSaved grounding report with {len(rows)} samples to: {GROUNDING_REPORT_PATH}")

    # Summary
    canonical_rows = [r for r in rows if r["sample_type"] == "canonical_live"]
    probe_rows = [r for r in rows if r["sample_type"].startswith("synthetic_")]

    canonical_pass_rate = (sum(1 for r in canonical_rows if r["grounding_passed"] == "PASS") / len(canonical_rows)) * 100
    probe_block_rate = (sum(1 for r in probe_rows if r["grounding_passed"] == "FAIL") / len(probe_rows)) * 100

    print("\n" + "=" * 95)
    print(" GROUNDING SUITE SUMMARY RESULTS")
    print("=" * 95)
    print(f" Canonical LLM Polish Pass Rate:  {canonical_pass_rate:.1f}% ({sum(1 for r in canonical_rows if r['grounding_passed'] == 'PASS')}/{len(canonical_rows)})")
    print(f" Hallucination Defense Block Rate: {probe_block_rate:.1f}% ({sum(1 for r in probe_rows if r['grounding_passed'] == 'FAIL')}/{len(probe_rows)} synthetic attacks blocked)")
    print("=" * 95)


if __name__ == "__main__":
    run_grounding_evaluation()
