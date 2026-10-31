"""Hybrid Convex Fusion Retrieval Engine ('hyb').

Combines dense semantic embeddings and sparse lexical TF-IDF per Section 4.2:
Score_hyb(Q, f_i) = alpha * Score_emb(Q, f_i) + (1 - alpha) * Score_tf(Q, f_i)
"""
from src.retrievers.base import BaseRetriever
from src.retrievers.embedding import EmbeddingRetriever
from src.retrievers.tfidf import TfidfRetriever


class HybridRetriever(BaseRetriever):
    """Convex combination of dense embeddings and sparse TF-IDF."""

    def __init__(self, alpha: float = 0.70):
        super().__init__(method_name="Hybrid (Dense+Sparse)", method_code="hyb")
        self.alpha = float(alpha)
        self.emb_retriever = EmbeddingRetriever(include_keywords=False)
        self.tf_retriever = TfidfRetriever()

    def fit(self, faqs: list[dict]) -> None:
        """Fit both underlying retrieval engines on the FAQ corpus."""
        self.faqs = list(faqs)
        self.emb_retriever.fit(self.faqs)
        self.tf_retriever.fit(self.faqs)

    def query(self, text: str, top_k: int = 3, category: str = "All") -> list[dict]:
        """Rank FAQs based on convex combination of embedding and TF-IDF scores."""
        if not self.faqs:
            return []

        # Query both retrievers across all FAQs in the selected category
        total_faqs = len(self.faqs)
        emb_results = self.emb_retriever.query(text, top_k=total_faqs, category=category)
        tf_results = self.tf_retriever.query(text, top_k=total_faqs, category=category)

        # Map FAQ ID to score
        emb_score_map = {item["id"]: item["score"] for item in emb_results}
        tf_score_map = {item["id"]: item["score"] for item in tf_results}

        scored_candidates = []
        for f in self._filter_faqs(category):
            faq_id = f["id"]
            s_emb = emb_score_map.get(faq_id, 0.0)
            s_tf = tf_score_map.get(faq_id, 0.0)

            score_hyb = self.alpha * s_emb + (1.0 - self.alpha) * s_tf
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
