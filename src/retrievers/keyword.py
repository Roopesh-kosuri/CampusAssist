"""Keyword Overlap Retrieval Engine ('kw').

Implements normalized query-token overlap with phrasal bigram bonus per Section 4.2.
"""
from src.preprocess import preprocess_lexical
from src.retrievers.base import BaseRetriever


class KeywordRetriever(BaseRetriever):
    """Normalized query-coverage overlap retriever with bigram phrase bonus."""

    def __init__(self):
        super().__init__(method_name="Keyword", method_code="kw")
        self.doc_unigrams: list[set[str]] = []
        self.doc_bigrams: list[set[str]] = []

    def fit(self, faqs: list[dict]) -> None:
        """Preprocess and index FAQ questions and keyword lists."""
        self.faqs = list(faqs)
        self.doc_unigrams = []
        self.doc_bigrams = []

        for f in self.faqs:
            text = f["question"] + " " + " ".join(f.get("keywords", []))
            u, b = preprocess_lexical(text)
            self.doc_unigrams.append(set(u))
            self.doc_bigrams.append(set(b))

    def query(self, text: str, top_k: int = 3, category: str = "All") -> list[dict]:
        """Rank FAQs based on query-coverage overlap."""
        if not self.faqs:
            return []

        q_u, q_b = preprocess_lexical(text)
        set_q_u = set(q_u)
        set_q_b = set(q_b)

        len_u = len(set_q_u)
        len_b = len(set_q_b)

        scored_candidates = []
        for idx, f in enumerate(self.faqs):
            if category != "All" and f.get("category") != category:
                continue

            if len_u == 0:
                score = 0.0
            else:
                doc_u = self.doc_unigrams[idx]
                doc_b = self.doc_bigrams[idx]

                overlap_u = len(set_q_u & doc_u) / max(1, len_u)
                overlap_b = len(set_q_b & doc_b) / max(1, len_b) if len_b > 0 else 0.0

                raw_score = 0.85 * overlap_u + 0.15 * overlap_b
                score = max(0.0, min(1.0, float(raw_score)))

            scored_candidates.append({
                "id": f["id"],
                "question": f["question"],
                "answer": f["answer"],
                "category": f["category"],
                "department_contact": f["department_contact"],
                "score": round(score, 4)
            })

        scored_candidates.sort(key=lambda x: x["score"], reverse=True)
        return scored_candidates[:top_k]
