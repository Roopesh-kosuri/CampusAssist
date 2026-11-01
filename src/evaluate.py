"""Deterministic offline evaluation engine for CampusAssist.

Evaluates kw, tf, emb, emb_kw, and hyb retrievers across test and dev splits.
Computes Top-1, Top-3, MRR, bootstrap 95% confidence intervals (1,000 resamples),
per-paraphrase-type breakdowns, query latencies, and out-of-scope rejection rates.
"""
import argparse
import csv
import json
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import numpy as np

# Enforce offline mode for Hugging Face to ensure 100% reproducible offline runs
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

from src.config import (
    FAQS_PATH,
    PARAPHRASES_PATH,
    OUT_OF_SCOPE_PATH,
    RESULTS_DIR,
    METRICS_PATH,
    THRESHOLDS_PATH,
    PER_TYPE_ACCURACY_PATH,
    FAILURE_CASES_PATH,
)
from src.validate_data import load_faqs, load_csv_rows
from src.retrievers.keyword import KeywordRetriever
from src.retrievers.tfidf import TfidfRetriever
from src.retrievers.embedding import EmbeddingRetriever
from src.retrievers.hybrid import HybridRetriever


def compute_bootstrap_ci(scores: list[float], n_bootstrap: int = 1000, seed: int = 42) -> tuple[float, float]:
    """Compute 95% bootstrap confidence interval with fixed random seed."""
    if not scores:
        return 0.0, 0.0
    rng = np.random.default_rng(seed)
    n = len(scores)
    indices = rng.integers(0, n, size=(n_bootstrap, n))
    arr = np.array(scores)
    resamples = np.mean(arr[indices], axis=1)
    ci_lower = float(np.percentile(resamples, 2.5))
    ci_upper = float(np.percentile(resamples, 97.5))
    return round(ci_lower, 4), round(ci_upper, 4)


def load_calibrated_thresholds() -> dict[str, float]:
    """Load calibrated thresholds from results/thresholds.json if present, else defaults."""
    default_thresholds = {"kw": 0.40, "tf": 0.35, "emb": 0.50, "emb_kw": 0.50, "hyb": 0.45}
    if THRESHOLDS_PATH.exists():
        try:
            with open(THRESHOLDS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("thresholds", default_thresholds)
        except Exception:
            pass
    return default_thresholds


def run_evaluation(split: str = "test", seed: int = 42) -> dict:
    """Run full evaluation suite across the specified split."""
    RESULTS_DIR.mkdir(exist_ok=True)
    faqs = load_faqs(FAQS_PATH)
    all_paraphrases = load_csv_rows(PARAPHRASES_PATH)
    all_oos = load_csv_rows(OUT_OF_SCOPE_PATH)

    # Filter by split
    queries = [row for row in all_paraphrases if row.get("split") == split]
    oos_queries = [row for row in all_oos if row.get("split") == split]

    if not queries:
        raise ValueError(f"No queries found for split '{split}' in {PARAPHRASES_PATH}")

    print("=" * 115)
    print(f" CampusAssist Deterministic Evaluation Engine (Split: {split.upper()})")
    print(f" Dataset: {len(queries)} paraphrased student queries | {len(oos_queries)} out-of-scope queries")
    print(f" Evaluated under offline constraints: HF_HUB_OFFLINE=1")
    print("=" * 115)

    # Instantiate retrievers
    print("Initializing and fitting all 5 retrieval configurations...")
    kw = KeywordRetriever()
    kw.fit(faqs)

    tf = TfidfRetriever()
    tf.fit(faqs)

    emb = EmbeddingRetriever(include_keywords=False)
    emb.fit(faqs)

    emb_kw = EmbeddingRetriever(include_keywords=True)
    emb_kw.fit(faqs)

    hyb = HybridRetriever(alpha=0.55)
    hyb.fit(faqs)

    engines = [
        ("kw", "Keyword Overlap", kw),
        ("tf", "TF-IDF Cosine", tf),
        ("emb", "Dense Embeddings", emb),
        ("emb_kw", "Embeddings + KW (Ablation)", emb_kw),
        ("hyb", "Hybrid Fusion (a=0.55)", hyb),
    ]

    thresholds = load_calibrated_thresholds()

    metrics_out = {
        "split": split,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "num_queries": len(queries),
        "num_oos": len(oos_queries),
        "random_seed": seed,
        "thresholds_used": thresholds,
        "methods": {}
    }

    per_type_rows = []
    failure_rows = []

    # Evaluation loop
    for code, display_name, retriever in engines:
        top1_hits = []
        top3_hits = []
        reciprocal_ranks = []
        latencies_ms = []

        # Breakdown by paraphrase_type
        by_type_hits = defaultdict(list)

        for row in queries:
            q_text = row["paraphrase"]
            target_id = row["faq_id"]
            ptype = row["paraphrase_type"]

            t0 = time.perf_counter()
            candidates = retriever.query(q_text, top_k=3, category="All")
            elapsed_ms = (time.perf_counter() - t0) * 1000
            latencies_ms.append(elapsed_ms)

            # Check ranking
            top1_hit = 1.0 if (candidates and candidates[0]["id"] == target_id) else 0.0
            top3_hit = 1.0 if any(c["id"] == target_id for c in candidates) else 0.0

            rr = 0.0
            for rank_idx, c in enumerate(candidates, 1):
                if c["id"] == target_id:
                    rr = 1.0 / rank_idx
                    break

            top1_hits.append(top1_hit)
            top3_hits.append(top3_hit)
            reciprocal_ranks.append(rr)
            by_type_hits[ptype].append(top1_hit)

            # Log failure cases
            if top1_hit == 0.0:
                pred_id = candidates[0]["id"] if candidates else "NONE"
                pred_score = candidates[0]["score"] if candidates else 0.0
                pred_q = candidates[0]["question"] if candidates else ""
                failure_rows.append({
                    "split": split,
                    "method": code,
                    "paraphrase_type": ptype,
                    "query": q_text,
                    "expected_id": target_id,
                    "predicted_id": pred_id,
                    "predicted_score": pred_score,
                    "predicted_question": pred_q
                })

        # Evaluate Out-of-Scope Rejection Rate
        tau = thresholds.get(code, 0.50)
        oos_rejections = 0
        for oos_row in oos_queries:
            oos_text = oos_row["query"]
            cands = retriever.query(oos_text, top_k=1, category="All")
            top_score = cands[0]["score"] if cands else 0.0
            if top_score < tau:
                oos_rejections += 1

        oos_rej_rate = (oos_rejections / len(oos_queries) * 100) if oos_queries else 0.0

        # Compute aggregate metrics and Bootstrap 95% CIs
        t1_mean = float(np.mean(top1_hits)) * 100
        t3_mean = float(np.mean(top3_hits)) * 100
        mrr_mean = float(np.mean(reciprocal_ranks))

        t1_ci_low, t1_ci_high = compute_bootstrap_ci(top1_hits, n_bootstrap=1000, seed=seed)
        t3_ci_low, t3_ci_high = compute_bootstrap_ci(top3_hits, n_bootstrap=1000, seed=seed)
        mrr_ci_low, mrr_ci_high = compute_bootstrap_ci(reciprocal_ranks, n_bootstrap=1000, seed=seed)

        lat_mean = float(np.mean(latencies_ms))
        lat_p95 = float(np.percentile(latencies_ms, 95))

        # Per-type breakdown
        per_type_top1 = {}
        for ptype, hits in sorted(by_type_hits.items()):
            acc = float(np.mean(hits)) * 100
            per_type_top1[ptype] = round(acc, 2)
            per_type_rows.append({
                "method": code,
                "paraphrase_type": ptype,
                "count": len(hits),
                "top1_correct": int(sum(hits)),
                "top1_acc": round(acc, 2)
            })

        metrics_out["methods"][code] = {
            "name": display_name,
            "top1_acc": round(t1_mean, 2),
            "top1_ci_95": [round(t1_ci_low * 100, 2), round(t1_ci_high * 100, 2)],
            "top3_acc": round(t3_mean, 2),
            "top3_ci_95": [round(t3_ci_low * 100, 2), round(t3_ci_high * 100, 2)],
            "mrr": round(mrr_mean, 4),
            "mrr_ci_95": [mrr_ci_low, mrr_ci_high],
            "latency_mean_ms": round(lat_mean, 2),
            "latency_p95_ms": round(lat_p95, 2),
            "threshold_used": tau,
            "oos_rejection_rate": round(oos_rej_rate, 2),
            "per_type_top1": per_type_top1
        }

    # Save outputs
    with open(METRICS_PATH, "w", encoding="utf-8") as f:
        json.dump(metrics_out, f, indent=2)

    with open(PER_TYPE_ACCURACY_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["method", "paraphrase_type", "count", "top1_correct", "top1_acc"])
        writer.writeheader()
        writer.writerows(per_type_rows)

    with open(FAILURE_CASES_PATH, "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "split", "method", "paraphrase_type", "query",
            "expected_id", "predicted_id", "predicted_score", "predicted_question"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(failure_rows)

    # Print Formatted Summary Tables
    print("\n" + "=" * 115)
    print(" SUMMARY BENCHMARK TABLE (With Bootstrap 95% Confidence Intervals)")
    print("=" * 115)
    hdr = f"{'Method':<20} | {'Top-1 (%) [95% CI]':<26} | {'Top-3 (%) [95% CI]':<26} | {'MRR [95% CI]':<22} | {'Lat (ms)':<9} | {'OOS Rej %':<9}"
    print(hdr)
    print("-" * 115)

    for code, m in metrics_out["methods"].items():
        t1_str = f"{m['top1_acc']:.1f}% [{m['top1_ci_95'][0]:.1f}-{m['top1_ci_95'][1]:.1f}]"
        t3_str = f"{m['top3_acc']:.1f}% [{m['top3_ci_95'][0]:.1f}-{m['top3_ci_95'][1]:.1f}]"
        mrr_str = f"{m['mrr']:.3f} [{m['mrr_ci_95'][0]:.3f}-{m['mrr_ci_95'][1]:.3f}]"
        lat_str = f"{m['latency_mean_ms']:.1f}"
        oos_str = f"{m['oos_rejection_rate']:.1f}%"
        row_str = f"{m['name']:<20} | {t1_str:<26} | {t3_str:<26} | {mrr_str:<22} | {lat_str:<9} | {oos_str:<9}"
        print(row_str)

    print("=" * 115)

    # Print Per-Paraphrase-Type Breakdown Table
    print("\n" + "=" * 115)
    print(" TOP-1 ACCURACY BY PARAPHRASE TYPE (%)")
    print("=" * 115)
    types_list = sorted(list({r["paraphrase_type"] for r in per_type_rows}))
    hdr_types = f"{'Method':<20} | " + " | ".join([f"{t:^13}" for t in types_list])
    print(hdr_types)
    print("-" * 115)

    for code, m in metrics_out["methods"].items():
        vals = [f"{m['per_type_top1'].get(t, 0.0):.1f}%" for t in types_list]
        row_type = f"{m['name']:<20} | " + " | ".join([f"{v:^13}" for v in vals])
        print(row_type)

    print("=" * 115)
    print(f"\nArtifacts saved successfully:")
    print(f"  -> {METRICS_PATH}")
    print(f"  -> {PER_TYPE_ACCURACY_PATH}")
    print(f"  -> {FAILURE_CASES_PATH} ({len(failure_rows)} failure records logged for error analysis)")
    print("=" * 115)

    return metrics_out


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate CampusAssist retrievers.")
    parser.add_argument("--split", choices=["test", "dev"], default="test", help="Dataset split to evaluate")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for bootstrap resampling")
    args = parser.parse_args()

    run_evaluation(split=args.split, seed=args.seed)
