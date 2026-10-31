"""Interactive benchmark comparing kw, tf, emb, and hyb across 10 sample queries."""
import time
from src.validate_data import load_faqs
from src.retrievers.keyword import KeywordRetriever
from src.retrievers.tfidf import TfidfRetriever
from src.retrievers.embedding import EmbeddingRetriever
from src.retrievers.hybrid import HybridRetriever

SAMPLE_QUERIES = [
    ("Exact match", "What are the central library opening and closing hours?", "lib_01"),
    ("Synonym swap", "When does the library shut down at night?", "lib_01"),
    ("Zero overlap", "My ceiling fan is making a grinding noise and stopped spinning", "hos_01"),
    ("Hinglish mixed", "bhai hostel room ka pankha kharab ho gaya kahan complain karu", "hos_01"),
    ("Typo query", "how to aply for duplcate id crd in lpu", "idc_01"),
    ("Reorder", "For semester tuition payment, what is the online portal process?", "fee_01"),
    ("Attendance rule", "What is the minimum attendance required to appear in exams?", "exm_02"),
    ("Turnstile chip", "RFID card not scanning at turnstiles and mess", "idc_04"),
    ("Bus schedule", "Where can I check day scholar bus routes and timings?", "trn_01"),
    ("Leave outpass", "How do I take leave and go home for weekend from hostel?", "hos_03"),
]


def run_benchmark():
    print("=" * 110)
    print(" CampusAssist: 10-Query Live Comparative Benchmark (kw vs tf vs emb vs hyb)")
    print("=" * 110)

    faqs = load_faqs()

    print("Initializing and fitting all 4 retrieval engines...")
    kw = KeywordRetriever()
    kw.fit(faqs)

    tf = TfidfRetriever()
    tf.fit(faqs)

    emb = EmbeddingRetriever(include_keywords=False)
    emb.fit(faqs)

    hyb = HybridRetriever(alpha=0.70)
    hyb.fit(faqs)

    models = [("kw", kw), ("tf", tf), ("emb", emb), ("hyb", hyb)]

    header = f"{'#':<3} | {'Query Type':<16} | {'Target':<6} | " + " | ".join(
        [f"{m[0].upper():^17}" for m in models]
    )
    print("\n" + header)
    print("-" * 110)

    for idx, (qtype, query_text, target) in enumerate(SAMPLE_QUERIES, 1):
        cols = []
        for code, model in models:
            t0 = time.perf_counter()
            res = model.query(query_text, top_k=1, category="All")
            dt_ms = (time.perf_counter() - t0) * 1000

            if res:
                top1_id = res[0]["id"]
                top1_score = res[0]["score"]
                match_mark = "OK" if top1_id == target else "XX"
                cols.append(f"{top1_id} ({top1_score:.2f}) [{match_mark}]")
            else:
                cols.append("NONE (0.00) [XX]")

        row = f"{idx:<3} | {qtype:<16} | {target:<6} | " + " | ".join(
            [f"{c:^17}" for c in cols]
        )
        print(row)

    print("=" * 110)
    print("Legend: [OK] = Correct Top-1 FAQ matched  |  [XX] = Failed to rank target FAQ #1")
    print("=" * 110)


if __name__ == "__main__":
    run_benchmark()
