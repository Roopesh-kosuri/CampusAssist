"""Unit tests for the retrieval engine suite ('kw', 'tf', 'emb', 'emb_kw', 'hyb')."""
import pytest
import numpy as np

from src.validate_data import load_faqs
from src.retrievers.keyword import KeywordRetriever
from src.retrievers.tfidf import TfidfRetriever
from src.retrievers.embedding import EmbeddingRetriever
from src.retrievers.hybrid import HybridRetriever
from src.config import PROJECT_ROOT


@pytest.fixture(scope="module")
def faqs():
    """Load canonical FAQs once for retriever testing."""
    return load_faqs()


@pytest.fixture(scope="module")
def retrievers(faqs):
    """Instantiate and fit all 5 retriever configurations."""
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

    return {
        "kw": kw,
        "tf": tf,
        "emb": emb,
        "emb_kw": emb_kw,
        "hyb": hyb
    }


@pytest.mark.parametrize("method_code", ["kw", "tf", "emb", "emb_kw", "hyb"])
def test_retriever_score_bounds_and_structure(retrievers, method_code):
    """Verify that all retrievers return valid schema and scores bounded in [0.0, 1.0]."""
    retriever = retrievers[method_code]
    results = retriever.query("How do I pay my semester fee online?", top_k=3, category="All")

    assert len(results) == 3, f"{method_code} should return top 3 items"
    required_keys = {"id", "question", "answer", "category", "department_contact", "score"}

    for idx, item in enumerate(results):
        assert required_keys.issubset(item.keys()), f"{method_code} item missing keys"
        score = item["score"]
        assert 0.0 <= score <= 1.0, f"{method_code} score {score} out of bounds [0.0, 1.0]"
        if idx > 0:
            assert score <= results[idx - 1]["score"], f"{method_code} results must be sorted descending"


@pytest.mark.parametrize("method_code", ["kw", "tf", "emb", "hyb"])
def test_category_filtering(retrievers, method_code):
    """Verify that specifying category strictly restricts candidates."""
    retriever = retrievers[method_code]
    results = retriever.query("What time does it close?", top_k=3, category="Library")

    assert len(results) > 0
    for item in results:
        assert item["category"] == "Library", f"{method_code} returned non-Library item under Library filter"


@pytest.mark.parametrize("method_code", ["kw", "tf", "emb", "hyb"])
def test_empty_and_gibberish_query_resilience(retrievers, method_code):
    """Verify that empty strings, whitespace, and punctuation do not crash the engines."""
    retriever = retrievers[method_code]
    for q in ["", "   ", "???!!!...", "$$##@@"]:
        results = retriever.query(q, top_k=3, category="All")
        assert isinstance(results, list)
        for r in results:
            assert 0.0 <= r["score"] <= 1.0


def test_embedding_disk_cache_created(faqs):
    """Verify that FAISS embeddings are persisted to .cache directory."""
    cache_dir = PROJECT_ROOT / ".cache"
    assert cache_dir.exists()

    cache_files = list(cache_dir.glob("emb_plain_*.npy"))
    assert len(cache_files) >= 1, "Expected cached .npy embedding file in .cache"

    # Verify cached file is valid numpy array with shape (72, 384)
    cached_arr = np.load(cache_files[0])
    assert cached_arr.shape == (72, 384)


def test_zero_overlap_paraphrase_semantic_advantage(retrievers):
    """Scientific test: Dense Embeddings must rank the correct FAQ #1 while Keyword matching fails on zero-overlap."""
    query = "My ceiling fan is making a grinding noise and stopped spinning"
    target_faq_id = "hos_01"  # "How do I register a hostel room maintenance complaint?"

    kw_res = retrievers["kw"].query(query, top_k=3, category="All")
    emb_res = retrievers["emb"].query(query, top_k=3, category="All")

    # emb should rank target FAQ as Top-1 because of semantic understanding
    assert emb_res[0]["id"] == target_faq_id, f"Expected {target_faq_id} at Top-1 for emb, got {emb_res[0]['id']}"

    # kw must fail to identify the target FAQ at Top-1 due to zero token overlap
    assert kw_res[0]["id"] != target_faq_id, f"Keyword should fail on zero-overlap, but got {kw_res[0]['id']}"

    # Find scores for target FAQ in both methods
    emb_score = emb_res[0]["score"]
    kw_target = next((item for item in kw_res if item["id"] == target_faq_id), None)
    kw_score = kw_target["score"] if kw_target else 0.0

    # Dense semantic score must strictly exceed Keyword score
    assert emb_score > kw_score, f"Embedding score ({emb_score}) should exceed Keyword score ({kw_score})"
