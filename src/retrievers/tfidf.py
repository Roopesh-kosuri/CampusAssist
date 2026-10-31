"""TF-IDF Cosine Similarity Retrieval Engine ('tf').

Implements sparse vector space retrieval with sublinear term-frequency scaling
and smoothed inverse document frequency per Section 4.2.
"""
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from src.preprocess import preprocess_lexical
from src.retrievers.base import BaseRetriever


def _lexical_analyzer(text: str) -> list[str]:
    """Analyzer extracting lexical unigram and bigram tokens."""
    unigrams, bigrams = preprocess_lexical(text)
    return unigrams + bigrams


class TfidfRetriever(BaseRetriever):
    """Sparse Vector Space Model retriever using TF-IDF and Cosine Similarity."""

    def __init__(self):
        super().__init__(method_name="TF-IDF", method_code="tf")
        self.vectorizer = TfidfVectorizer(
            analyzer=_lexical_analyzer,
            sublinear_tf=True,
            smooth_idf=True,
            norm="l2"
        )
        self.tfidf_matrix = None

    def fit(self, faqs: list[dict]) -> None:
        """Fit TF-IDF vocabulary on FAQ questions and keyword lists."""
        self.faqs = list(faqs)
        corpus = [
            f["question"] + " " + " ".join(f.get("keywords", []))
            for f in self.faqs
        ]
        self.tfidf_matrix = self.vectorizer.fit_transform(corpus)

    def query(self, text: str, top_k: int = 3, category: str = "All") -> list[dict]:
        """Rank FAQs based on cosine similarity with the query vector."""
        if not self.faqs or self.tfidf_matrix is None:
            return []

        # Transform query into sparse TF-IDF vector
        query_vec = self.vectorizer.transform([text])
        # Inner product of L2-normalized sparse vectors equals cosine similarity
        similarities = (self.tfidf_matrix.dot(query_vec.T)).toarray().flatten()

        scored_candidates = []
        for idx, f in enumerate(self.faqs):
            if category != "All" and f.get("category") != category:
                continue

            sim = similarities[idx]
            # Handle numerical imprecision and clamp to [0.0, 1.0]
            clamped_sim = max(0.0, min(1.0, float(sim)))

            scored_candidates.append({
                "id": f["id"],
                "question": f["question"],
                "answer": f["answer"],
                "category": f["category"],
                "department_contact": f["department_contact"],
                "score": round(clamped_sim, 4)
            })

        scored_candidates.sort(key=lambda x: x["score"], reverse=True)
        return scored_candidates[:top_k]
