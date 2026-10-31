"""Smoke test to verify environment dependencies and embedding model."""
import pytest
import numpy as np


def test_python_environment():
    """Verify standard library imports and python version."""
    import sys
    assert sys.version_info >= (3, 10), "Python 3.10+ required"


def test_sentence_transformer_loading():
    """Verify that all-MiniLM-L6-v2 loads on CPU and produces unit-normalized (1, 384) vectors."""
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
    text = "What time does the Central Library close?"
    embedding = model.encode([text], normalize_embeddings=True)

    assert isinstance(embedding, np.ndarray), "Embedding must be a numpy ndarray"
    assert embedding.shape == (1, 384), f"Expected shape (1, 384), got {embedding.shape}"

    # Verify unit L2 normalization: ||v||_2 ≈ 1.0
    norm = np.linalg.norm(embedding[0])
    assert abs(norm - 1.0) < 1e-4, f"Vector should be L2-normalized to 1.0, got norm {norm}"


def test_faiss_cpu_index():
    """Verify that FAISS CPU IndexFlatIP is functional."""
    import faiss

    dim = 384
    index = faiss.IndexFlatIP(dim)
    assert index.d == dim
    assert index.ntotal == 0

    # Add a dummy vector
    vec = np.random.randn(1, dim).astype("float32")
    vec = vec / np.linalg.norm(vec)
    index.add(vec)
    assert index.ntotal == 1

    # Query the index
    scores, indices = index.search(vec, 1)
    assert indices[0][0] == 0
    assert abs(scores[0][0] - 1.0) < 1e-4
