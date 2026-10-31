"""Per-method threshold calibration module for CampusAssist.

Tuning strictly executed on the DEV split (paraphrases.csv[dev] + out_of_scope.csv[dev]).
Sweeps tau in [0.10, 0.95] (step 0.01) to maximize the harmonic mean of In-Scope
Answered Precision and Out-of-Scope Rejection Rate subject to Coverage >= 0.75.
Saves results/thresholds.json, results/score_distributions.json, and updates
results/metrics.json on the test split.
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
import numpy as np

# Offline guarantee
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

from src.config import (
    FAQS_PATH,
    PARAPHRASES_PATH,
    OUT_OF_SCOPE_PATH,
    RESULTS_DIR,
    THRESHOLDS_PATH,
    METRICS_PATH,
)
from src.validate_data import load_faqs, load_csv_rows
from src.retrievers.keyword import KeywordRetriever
from src.retrievers.tfidf import TfidfRetriever
from src.retrievers.embedding import EmbeddingRetriever
from src.retrievers.hybrid import HybridRetriever
from src.evaluate import run_evaluation


def summarize_distribution(arr: np.ndarray) -> dict:
    """Compute summary percentiles and statistical moments."""
    if len(arr) == 0:
        return {"count": 0, "mean": 0.0, "median": 0.0, "std": 0.0, "p10": 0.0, "p90": 0.0}
    return {
        "count": int(len(arr)),
        "mean": round(float(np.mean(arr)), 4),
        "median": round(float(np.median(arr)), 4),
        "std": round(float(np.std(arr)), 4),
        "min": round(float(np.min(arr)), 4),
        "p10": round(float(np.percentile(arr, 10)), 4),
        "p25": round(float(np.percentile(arr, 25)), 4),
        "p75": round(float(np.percentile(arr, 75)), 4),
        "p90": round(float(np.percentile(arr, 90)), 4),
        "max": round(float(np.max(arr)), 4)
    }


def calibrate_thresholds() -> dict:
    """Tune similarity thresholds per method on the dev split."""
    RESULTS_DIR.mkdir(exist_ok=True)
    faqs = load_faqs(FAQS_PATH)
    all_paraphrases = load_csv_rows(PARAPHRASES_PATH)
    all_oos = load_csv_rows(OUT_OF_SCOPE_PATH)

    # STRICT DEV SPLIT ISOLATION
    dev_queries = [r for r in all_paraphrases if r.get("split") == "dev"]
    dev_oos = [r for r in all_oos if r.get("split") == "dev"]

    print("=" * 105)
    print(" CampusAssist Per-Method Threshold Calibration")
    print(f" Tuned strictly on DEV split: {len(dev_queries)} in-scope queries | {len(dev_oos)} OOS queries")
    print(" Target criteria: Max harmonic utility of Precision & OOS Rejection subject to Coverage >= 0.75")
    print("=" * 105)

    # Initialize engines
    kw = KeywordRetriever()
    kw.fit(faqs)

    tf = TfidfRetriever()
    tf.fit(faqs)

    emb = EmbeddingRetriever(include_keywords=False)
    emb.fit(faqs)

    emb_kw = EmbeddingRetriever(include_keywords=True)
    emb_kw.fit(faqs)

    hyb = HybridRetriever(alpha=0.70)
    hyb.fit(faqs)

    engines = [
        ("kw", "Keyword Overlap", kw),
        ("tf", "TF-IDF Cosine", tf),
        ("emb", "Dense Embeddings", emb),
        ("emb_kw", "Embeddings + KW", emb_kw),
        ("hyb", "Hybrid Fusion", hyb),
    ]

    candidate_thresholds = np.round(np.arange(0.10, 0.96, 0.01), 2)
    calibrated_thresholds = {}
    calibration_metrics = {}
    distributions_out = {}

    for code, display_name, retriever in engines:
        # Precompute top candidate scores on dev
        in_scope_scores = []
        in_scope_correct = []
        for row in dev_queries:
            q = row["paraphrase"]
            target_id = row["faq_id"]
            res = retriever.query(q, top_k=1, category="All")
            score = res[0]["score"] if res else 0.0
            is_correct = 1.0 if (res and res[0]["id"] == target_id) else 0.0
            in_scope_scores.append(score)
            in_scope_correct.append(is_correct)

        oos_scores = []
        for row in dev_oos:
            q = row["query"]
            res = retriever.query(q, top_k=1, category="All")
            score = res[0]["score"] if res else 0.0
            oos_scores.append(score)

        in_scope_scores = np.array(in_scope_scores)
        in_scope_correct = np.array(in_scope_correct)
        oos_scores = np.array(oos_scores)

        # Record score distributions for analysis
        correct_scores = in_scope_scores[in_scope_correct == 1.0]
        distributions_out[code] = {
            "name": display_name,
            "correct_matches": summarize_distribution(correct_scores),
            "oos_queries": summarize_distribution(oos_scores)
        }

        # Sweep candidate thresholds
        best_tau = 0.50
        best_utility = -1.0
        best_stats = {}

        # First pass: try subject to coverage >= 0.75
        valid_candidates = []
        for tau in candidate_thresholds:
            answered_mask = in_scope_scores >= tau
            coverage = float(np.mean(answered_mask))
            if np.sum(answered_mask) > 0:
                precision = float(np.mean(in_scope_correct[answered_mask]))
            else:
                precision = 0.0
            oos_rejection = float(np.mean(oos_scores < tau))

            harmonic_utility = (2 * precision * oos_rejection) / (precision + oos_rejection + 1e-6)

            stats_dict = {
                "tau": float(tau),
                "coverage": round(coverage, 4),
                "precision": round(precision, 4),
                "oos_rejection": round(oos_rejection, 4),
                "utility": round(harmonic_utility, 4)
            }

            if coverage >= 0.75:
                valid_candidates.append(stats_dict)

        # Fallback if no threshold satisfies coverage >= 0.75
        if not valid_candidates:
            # Take top 3 thresholds by coverage and pick best utility
            all_sorted = sorted(
                [
                    {
                        "tau": float(t),
                        "coverage": float(np.mean(in_scope_scores >= t)),
                        "precision": float(np.mean(in_scope_correct[in_scope_scores >= t])) if np.sum(in_scope_scores >= t) > 0 else 0.0,
                        "oos_rejection": float(np.mean(oos_scores < t)),
                        "utility": float(
                            (2 * (np.mean(in_scope_correct[in_scope_scores >= t]) if np.sum(in_scope_scores >= t) > 0 else 0.0) * np.mean(oos_scores < t))
                            / ((np.mean(in_scope_correct[in_scope_scores >= t]) if np.sum(in_scope_scores >= t) > 0 else 0.0) + np.mean(oos_scores < t) + 1e-6)
                        )
                    }
                    for t in candidate_thresholds
                ],
                key=lambda x: x["coverage"],
                reverse=True
            )
            valid_candidates = all_sorted[:5]

        # Select maximum harmonic utility
        valid_candidates.sort(key=lambda x: x["utility"], reverse=True)
        optimal = valid_candidates[0]

        best_tau = optimal["tau"]
        calibrated_thresholds[code] = best_tau
        calibration_metrics[code] = {
            "name": display_name,
            "calibrated_threshold": best_tau,
            "dev_coverage_pct": round(optimal["coverage"] * 100, 2),
            "dev_precision_pct": round(optimal["precision"] * 100, 2),
            "dev_oos_rejection_pct": round(optimal["oos_rejection"] * 100, 2),
            "harmonic_utility": optimal["utility"]
        }

    # Save calibrated thresholds
    threshold_payload = {
        "tuned_on": "dev",
        "calibrated_at": datetime.now(timezone.utc).isoformat(),
        "objective": "Max harmonic mean of In-Scope Precision and OOS Rejection subject to Coverage >= 0.75",
        "thresholds": calibrated_thresholds,
        "metrics": calibration_metrics
    }
    with open(THRESHOLDS_PATH, "w", encoding="utf-8") as f:
        json.dump(threshold_payload, f, indent=2)

    # Save score distributions
    score_dist_path = RESULTS_DIR / "score_distributions.json"
    with open(score_dist_path, "w", encoding="utf-8") as f:
        json.dump(distributions_out, f, indent=2)

    # Print Calibration Summary Table
    print("\n" + "=" * 105)
    print(" CALIBRATED THRESHOLDS SUMMARY (Tuned on DEV Split)")
    print("=" * 105)
    header = f"{'Method':<20} | {'Threshold (tau*)':<16} | {'Coverage (Dev)':<16} | {'Precision (Dev)':<16} | {'OOS Rej (Dev)':<14} | {'Utility':<8}"
    print(header)
    print("-" * 105)

    for code, m in calibration_metrics.items():
        row_str = (
            f"{m['name']:<20} | "
            f"{m['calibrated_threshold']:<16.2f} | "
            f"{m['dev_coverage_pct']:<15.1f}% | "
            f"{m['dev_precision_pct']:<15.1f}% | "
            f"{m['dev_oos_rejection_pct']:<13.1f}% | "
            f"{m['harmonic_utility']:<8.3f}"
        )
        print(row_str)

    print("=" * 105)
    print(f"\nSaved calibrated thresholds to: {THRESHOLDS_PATH}")
    print(f"Saved score distribution statistics to: {score_dist_path}")

    # Re-evaluate on the TEST split to verify generalization
    print("\nRe-evaluating TEST split with freshly calibrated thresholds...")
    test_metrics = run_evaluation(split="test")

    return {
        "thresholds": calibrated_thresholds,
        "dev_metrics": calibration_metrics,
        "test_metrics": test_metrics
    }


if __name__ == "__main__":
    calibrate_thresholds()
