# CampusAssist · Lovely Professional University (LPU)
## CSE276 Artificial Intelligence Foundations — CA-1 Course Project
**Project 02:** Campus Service Chatbot with Semantic FAQ Matching

---

### Project Overview
CampusAssist is an intelligent campus service assistant evaluating four retrieval paradigms over an identical 72-FAQ knowledge base across 6 student service domains:
1. **Keyword Overlap (`kw`)**
2. **TF-IDF Cosine Similarity (`tf`)**
3. **Dense Sentence Embeddings (`emb`)** using `all-MiniLM-L6-v2` + FAISS
4. **Hybrid Convex Fusion (`hyb`)**

### Quick Start
```bash
# 1. Activate virtual environment
.venv\Scripts\activate

# 2. Run unit tests
pytest -v

# 3. Launch FastAPI backend
uvicorn app.main:app --reload --port 8000
```

### Rubric Mapping & Provenance
- Course: CSE276 Artificial Intelligence Foundations
- Session: 2026–27
- Model: `sentence-transformers/all-MiniLM-L6-v2` (Apache 2.0)
- All external libraries explicitly acknowledged per course guidelines. Zero unacknowledged reuse.
