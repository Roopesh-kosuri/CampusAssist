"""Hybrid Convex Fusion Retrieval Engine ('hyb').

Combines dense semantic embeddings and sparse lexical TF-IDF per Section 4.2:
Score_hyb(Q, f_i) = alpha * Score_emb(Q, f_i) + (1 - alpha) * Score_tf(Q, f_i)
"""
from src.retrievers.base import BaseRetriever
from src.retrievers.embedding import EmbeddingRetriever
from src.retrievers.tfidf import TfidfRetriever
from src.retrievers.keyword import KeywordRetriever


class HybridRetriever(BaseRetriever):
    """Hybrid Fusion combining rich dense semantic embeddings, sparse TF-IDF, and lexical keyword overlap."""

    def __init__(self, alpha: float = 0.55):
        super().__init__(method_name="Hybrid (Dense+Sparse)", method_code="hyb")
        self.alpha = float(alpha)
        # Rich multi-representation embeddings (include_keywords=True)
        self.emb_retriever = EmbeddingRetriever(include_keywords=True)
        self.tf_retriever = TfidfRetriever()
        self.kw_retriever = KeywordRetriever()

    def fit(self, faqs: list[dict]) -> None:
        """Fit all three underlying retrieval engines on the FAQ corpus."""
        self.faqs = list(faqs)
        self.emb_retriever.fit(self.faqs)
        self.tf_retriever.fit(self.faqs)
        self.kw_retriever.fit(self.faqs)

    def query(self, text: str, top_k: int = 3, category: str = "All") -> list[dict]:
        """Rank FAQs based on calibrated convex fusion of dense embeddings, TF-IDF, and keyword overlap."""
        if not self.faqs:
            return []

        # Query all retrievers across all FAQs in the selected category
        total_faqs = len(self.faqs)
        emb_results = self.emb_retriever.query(text, top_k=total_faqs, category=category)
        tf_results = self.tf_retriever.query(text, top_k=total_faqs, category=category)
        kw_results = self.kw_retriever.query(text, top_k=total_faqs, category=category)

        # Map FAQ ID to score
        emb_score_map = {item["id"]: item["score"] for item in emb_results}
        tf_score_map = {item["id"]: item["score"] for item in tf_results}
        kw_score_map = {item["id"]: item["score"] for item in kw_results}

        # Weight allocation: alpha to dense embeddings, remainder split between TF-IDF (2/3) and Keyword overlap (1/3)
        rem = 1.0 - self.alpha
        w_emb = self.alpha
        w_tf = rem * (2.0 / 3.0)
        w_kw = rem * (1.0 / 3.0)

        scored_candidates = []
        for f in self._filter_faqs(category):
            faq_id = f["id"]
            s_emb = emb_score_map.get(faq_id, 0.0)
            s_tf = tf_score_map.get(faq_id, 0.0)
            s_kw = kw_score_map.get(faq_id, 0.0)

            score_hyb = w_emb * s_emb + w_tf * s_tf + w_kw * s_kw
            clamped_score = max(0.0, min(1.0, float(score_hyb)))

            scored_candidates.append({
                "id": faq_id,
                "question": f["question"],
                "answer": f["answer"],
                "category": f["category"],
                "department_contact": f["department_contact"],
                "score": round(clamped_score, 4)
            })

        scored_candidates.sort(key=lambda x: x["score"], reverse=True)
        return scored_candidates[:top_k]
