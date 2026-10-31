"""Dense Sentence Embedding Retrieval Engine ('emb' & 'emb_kw').

Implements dense semantic retrieval using pre-trained all-MiniLM-L6-v2
projected into R^384, L2-normalized on S^383, and indexed in FAISS IndexFlatIP.
Includes SHA-256 disk caching for instant sub-second startups.
"""
import hashlib
import json
import numpy as np
import faiss
from pathlib import Path
from sentence_transformers import SentenceTransformer

from src.config import PROJECT_ROOT, EMBEDDING_MODEL_NAME, EMBEDDING_DIM
from src.preprocess import preprocess_semantic
from src.retrievers.base import BaseRetriever


class EmbeddingRetriever(BaseRetriever):
    """Dense Semantic Retriever powered by Sentence Transformers and FAISS."""

    def __init__(self, include_keywords: bool = False):
        code = "emb_kw" if include_keywords else "emb"
        name = "Semantic Embeddings (with Keywords)" if include_keywords else "Semantic Embeddings"
        super().__init__(method_name=name, method_code=code)

        self.include_keywords = include_keywords
        self.model = None
        self.index = None
        self.doc_embeddings: np.ndarray = None
        self.cache_dir = PROJECT_ROOT / ".cache"
        self.cache_dir.mkdir(exist_ok=True)

    def _get_model(self) -> SentenceTransformer:
        """Lazy-load SentenceTransformer on CPU."""
        if self.model is None:
            self.model = SentenceTransformer(EMBEDDING_MODEL_NAME, device="cpu")
        return self.model

    def _compute_faqs_hash(self, faqs: list[dict]) -> str:
        """Compute deterministic SHA-256 hash over the FAQ corpus."""
        serialized = json.dumps(faqs, sort_keys=True, ensure_ascii=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]

    def fit(self, faqs: list[dict]) -> None:
        """Encode or load cached FAQ embeddings and construct FAISS IndexFlatIP."""
        self.faqs = list(faqs)
        faq_hash = self._compute_faqs_hash(self.faqs)
        cache_mode = "kw" if self.include_keywords else "plain"
        cache_path = self.cache_dir / f"emb_{cache_mode}_{faq_hash}.npy"

        # Check for precomputed disk cache
        if cache_path.exists():
            try:
                self.doc_embeddings = np.load(cache_path).astype("float32")
            except Exception:
                self.doc_embeddings = None

        if self.doc_embeddings is None or self.doc_embeddings.shape != (len(self.faqs), EMBEDDING_DIM):
            # Generate document representations for embedding
            corpus = []
            for f in self.faqs:
                if self.include_keywords:
                    raw_text = f["question"] + " " + " ".join(f.get("keywords", []))
                else:
                    raw_text = f["question"]
                corpus.append(preprocess_semantic(raw_text))

            model = self._get_model()
            # Normalize embeddings to unit sphere S^383 so Inner Product == Cosine Similarity
            embeddings = model.encode(
                corpus,
                normalize_embeddings=True,
                show_progress_bar=False,
                convert_to_numpy=True
            ).astype("float32")

            self.doc_embeddings = embeddings
            # Persist to disk cache
            np.save(cache_path, self.doc_embeddings)

        # Build exact inner product FAISS index
        self.index = faiss.IndexFlatIP(EMBEDDING_DIM)
        self.index.add(self.doc_embeddings)

    def query(self, text: str, top_k: int = 3, category: str = "All") -> list[dict]:
        """Rank FAQs based on cosine similarity of dense semantic representations."""
        if not self.faqs or self.index is None:
            return []

        clean_query = preprocess_semantic(text)
        if not clean_query.strip():
            # Handle empty query gracefully
            return [
                {
                    "id": f["id"],
                    "question": f["question"],
                    "answer": f["answer"],
                    "category": f["category"],
                    "department_contact": f["department_contact"],
                    "score": 0.0
                }
                for f in self._filter_faqs(category)[:top_k]
            ]

        model = self._get_model()
        q_emb = model.encode(
            [clean_query],
            normalize_embeddings=True,
            show_progress_bar=False,
            convert_to_numpy=True
        ).astype("float32")

        # Search all FAQs to allow flexible post-filtering by category
        scores, indices = self.index.search(q_emb, len(self.faqs))
        scores = scores[0]
        indices = indices[0]

        scored_candidates = []
        for idx_rank, faq_idx in enumerate(indices):
            f = self.faqs[faq_idx]
            if category != "All" and f.get("category") != category:
                continue

            raw_sim = scores[idx_rank]
            clamped_sim = max(0.0, min(1.0, float(raw_sim)))

            scored_candidates.append({
                "id": f["id"],
                "question": f["question"],
                "answer": f["answer"],
                "category": f["category"],
                "department_contact": f["department_contact"],
                "score": round(clamped_sim, 4)
            })

            if len(scored_candidates) >= top_k:
                break

        return scored_candidates
