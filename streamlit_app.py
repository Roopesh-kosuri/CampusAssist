"""CampusAssist - Streamlit Syllabus-Compliant Evaluation and Query Interface.

Provides an interactive Streamlit dashboard allowing college evaluators to test
all 5 retrieval algorithms, inspect confidence scores, view fallback routing,
and review comparative offline benchmark tables.
"""
import json
import os
from pathlib import Path
import pandas as pd
import streamlit as st

# Offline execution guarantee
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

from src.config import FAQS_PATH, METRICS_PATH, THRESHOLDS_PATH, CATEGORIES
from src.validate_data import load_faqs
from src.retrievers.keyword import KeywordRetriever
from src.retrievers.tfidf import TfidfRetriever
from src.retrievers.embedding import EmbeddingRetriever
from src.retrievers.hybrid import HybridRetriever
from src.fallback import FallbackRouter

st.set_page_config(page_title="CampusAssist · LPU Campus FAQ", page_icon="🎓", layout="wide")


@st.cache_resource
def load_system():
    """Load canonical FAQs, initialize FallbackRouter, and fit all retrievers."""
    faqs = load_faqs(FAQS_PATH)
    router = FallbackRouter()
    router.reload_thresholds()

    kw = KeywordRetriever(); kw.fit(faqs)
    tf = TfidfRetriever(); tf.fit(faqs)
    emb = EmbeddingRetriever(include_keywords=False); emb.fit(faqs)
    emb_kw = EmbeddingRetriever(include_keywords=True); emb_kw.fit(faqs)
    hyb = HybridRetriever(alpha=0.70); hyb.fit(faqs)

    engines = {"kw": kw, "tf": tf, "emb": emb, "emb_kw": emb_kw, "hyb": hyb}
    return engines, router, faqs


engines, router, faqs = load_system()

# Sidebar Configuration
st.sidebar.title("🎓 CampusAssist")
st.sidebar.caption("LPU Campus FAQ Retrieval Engine · CSE276 CA-1")

method_labels = {
    "hyb": "Hybrid Fusion (a=0.70)",
    "emb": "Dense Embeddings (all-MiniLM-L6-v2)",
    "emb_kw": "Embeddings + KW Enrichment",
    "tf": "TF-IDF Cosine",
    "kw": "Keyword Overlap"
}
selected_code = st.sidebar.selectbox(
    "Retrieval Algorithm",
    options=list(method_labels.keys()),
    format_func=lambda k: method_labels[k]
)
selected_cat = st.sidebar.selectbox("Campus Category", options=CATEGORIES)

active_tau = router.get_threshold(selected_code)
st.sidebar.metric("Calibrated Threshold (tau*)", f"{active_tau:.2f}")
st.sidebar.info("Threshold calibrated on DEV split to maximize Answered Precision & OOS Rejection (Coverage >= 75%).")

tab_chat, tab_bench = st.tabs(["💬 Interactive Chat & Query", "📊 Scientific Evaluation & Metrics"])

with tab_chat:
    st.subheader("Campus Service FAQ Matching")
    st.caption(f"Active Method: **{method_labels[selected_code]}** | Category: **{selected_cat}** | Threshold: **{active_tau:.2f}**")

    # Sample query quick-fills
    st.write("**Quick sample queries:**")
    cols = st.columns(3)
    sample_queries = [
        "How do I register a hostel maintenance complaint?",
        "When does the central library close at night?",
        "I lost my student ID card, what to do?"
    ]
    query_input = ""
    for i, sq in enumerate(sample_queries):
        if cols[i].button(sq, key=f"sq_{i}"):
            query_input = sq

    user_query = st.chat_input("Ask about hostel, library, fees, ID cards, transport, or exams...") or query_input

    if user_query:
        with st.chat_message("user"):
            st.write(user_query)

        retriever = engines[selected_code]
        candidates = retriever.query(user_query, top_k=3, category=selected_cat)
        top_score = candidates[0]["score"] if candidates else 0.0
        is_fallback = router.should_fallback(top_score, selected_code)

        with st.chat_message("assistant"):
            if is_fallback or not candidates:
                dept_contact = router.get_department_contact(selected_cat)
                st.warning(f"⚠️ **Low Confidence Match ({top_score*100:.1f}% < {active_tau*100:.1f}%)**")
                st.write("I couldn't find a sufficiently close match in the campus FAQ knowledge base.")
                st.info(f"**Official Fallback Routing:** {dept_contact}")
            else:
                best = candidates[0]
                st.success(f"✅ **Matched FAQ: {best['question']}** (Confidence: **{top_score*100:.1f}%** | Category: **{best['category']}**)")
                st.markdown(f"**Answer:** {best['answer']}")
                st.caption(f"Department Contact: {best.get('department_contact', 'N/A')}")

            # Explainability candidate breakdown
            with st.expander("🔍 Top-3 Retrieval Diagnostics"):
                for idx, c in enumerate(candidates, 1):
                    st.write(f"**{idx}. [{c['id']}] {c['question']}** — Score: `{c['score']:.4f}` ({c['category']})")

with tab_bench:
    st.subheader("Comparative Offline Benchmark Results")
    st.caption("Evaluated on the 100% human-authored TEST split (144 paraphrases, 30 out-of-scope queries) under strict offline isolation.")

    if METRICS_PATH.exists():
        with open(METRICS_PATH, "r", encoding="utf-8") as f:
            metrics_data = json.load(f)

        m = metrics_data.get("methods", {})
        ths = metrics_data.get("thresholds_used", {})

        bench_rows = []
        for code, label in method_labels.items():
            if code in m:
                info = m[code]
                top1_ci = f"{info['top1_acc']:.1f}% [{info['top1_ci_95'][0]:.1f}-{info['top1_ci_95'][1]:.1f}]" if 'top1_ci_95' in info else f"{info['top1_acc']:.1f}%"
                top3_ci = f"{info['top3_acc']:.1f}% [{info['top3_ci_95'][0]:.1f}-{info['top3_ci_95'][1]:.1f}]" if 'top3_ci_95' in info else f"{info['top3_acc']:.1f}%"
                mrr_ci = f"{info['mrr']:.3f} [{info['mrr_ci_95'][0]:.3f}-{info['mrr_ci_95'][1]:.3f}]" if 'mrr_ci_95' in info else f"{info['mrr']:.3f}"
                bench_rows.append({
                    "Method": label,
                    "Top-1 (%) [95% CI]": top1_ci,
                    "Top-3 (%) [95% CI]": top3_ci,
                    "MRR [95% CI]": mrr_ci,
                    "OOS Rejection (%)": f"{info.get('oos_rejection_rate', 0):.1f}%",
                    "Threshold (tau*)": f"{ths.get(code, info.get('threshold_used', 0)):.2f}",
                    "Mean Latency (ms)": f"{info['latency_mean_ms']:.1f} ms"
                })

        st.dataframe(pd.DataFrame(bench_rows), use_container_width=True)

        st.markdown("### Accuracy by Paraphrase Challenge Type")
        type_rows = []
        for code, label in method_labels.items():
            if code in m and "per_type_top1" in m[code]:
                pt = m[code]["per_type_top1"]
                type_rows.append({
                    "Method": label,
                    "Hinglish Mixed": f"{pt.get('hinglish_mixed', 0):.1f}%",
                    "Low Overlap": f"{pt.get('low_overlap', 0):.1f}%",
                    "Reorder": f"{pt.get('reorder', 0):.1f}%",
                    "Synonym Swap": f"{pt.get('synonym_swap', 0):.1f}%",
                    "Typo": f"{pt.get('typo', 0):.1f}%",
                    "Verbose": f"{pt.get('verbose', 0):.1f}%"
                })
        st.dataframe(pd.DataFrame(type_rows), use_container_width=True)
    else:
        st.warning("Benchmark metrics file results/metrics.json not found. Run python -m src.evaluate first.")
