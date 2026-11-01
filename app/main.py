"""FastAPI Application for CampusAssist - LPU Campus FAQ Chatbot.

Provides REST API endpoints for configuration, query processing, student feedback,
analytics telemetry, and model evaluation metrics. Serves the Liquid Glass web UI.
"""
import json
import os
import re
import time
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# Offline guarantees
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

from src.config import (
    FAQS_PATH,
    METRICS_PATH,
    THRESHOLDS_PATH,
    FAILURE_CASES_PATH,
    CATEGORIES,
    APP_DIR,
)
from src.validate_data import load_faqs
from src.privacy import redact_pii
from src.analytics import log_query, record_feedback, get_analytics, init_db
from src.fallback import FallbackRouter
from src.retrievers.keyword import KeywordRetriever
from src.retrievers.tfidf import TfidfRetriever
from src.retrievers.embedding import EmbeddingRetriever
from src.retrievers.hybrid import HybridRetriever
from src.llm.groq_client import GroqPolisher
from src.llm.grounding_check import verify_grounding
from app.schemas import (
    ConfigResponse,
    MethodInfo,
    QueryRequest,
    QueryResponse,
    MatchedFaq,
    FeedbackRequest,
    FeedbackResponse,
)

# ---------------------------------------------------------------------------
# Auto-mode retrieval method classifier
# ---------------------------------------------------------------------------
_HINGLISH_TOKENS = {
    "bhai", "yaar", "kahan", "karo", "kaise", "kya", "mera", "meri",
    "ho", "gaya", "wala", "hai", "hain", "nahi", "nhi", "btao", "bta",
    "kab", "kyun", "isko", "usko", "hua", "karna", "chahiye", "please",
    "dude", "bro", "scene", "jugaad", "theek", "pata", "pls",
}

def auto_select_method(query: str) -> str:
    """Choose retrieval method automatically based on query characteristics."""
    tokens = set(query.lower().split())

    # Hinglish detected → semantic embeddings handle transliteration best
    if tokens & _HINGLISH_TOKENS:
        return "emb"

    # Very short queries with admin keywords → keyword is fast & precise
    words = query.split()
    admin_kws = {"fee", "hostel", "library", "timing", "contact", "number",
                 "hours", "open", "close", "shut", "bus"}
    if len(words) <= 6 and tokens & admin_kws:
        return "kw"

    # Default: hybrid gives best overall accuracy
    return "hyb"

# Global engine registry
engines = {}
fallback_router = None
faqs_data = []
polisher = None

METHOD_NORMALIZATION = {
    "keyword": "kw",
    "kw": "kw",
    "tfidf": "tf",
    "tf": "tf",
    "embedding": "emb",
    "emb": "emb",
    "emb_kw": "emb_kw",
    "hybrid": "hyb",
    "hyb": "hyb",
    "auto": "auto",
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize SQLite DB, load FAQ data, and fit all retrieval engines on startup."""
    global engines, fallback_router, faqs_data, polisher
    init_db()

    # Load canonical FAQs
    faqs_data = load_faqs(FAQS_PATH)

    # Initialize FallbackRouter
    fallback_router = FallbackRouter()
    fallback_router.reload_thresholds()

    # Initialize Groq Polisher
    polisher = GroqPolisher()

    # Fit retrievers
    kw = KeywordRetriever()
    kw.fit(faqs_data)

    tf = TfidfRetriever()
    tf.fit(faqs_data)

    emb = EmbeddingRetriever(include_keywords=False)
    emb.fit(faqs_data)

    emb_kw = EmbeddingRetriever(include_keywords=True)
    emb_kw.fit(faqs_data)

    hyb = HybridRetriever(alpha=0.55)
    hyb.fit(faqs_data)

    engines = {
        "kw": kw,
        "tf": tf,
        "emb": emb,
        "emb_kw": emb_kw,
        "hyb": hyb,
    }
    yield
    engines.clear()


app = FastAPI(
    title="CampusAssist API",
    description="Campus Service Chatbot with Semantic FAQ Matching for Lovely Professional University",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for local development and testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files mount
static_dir = APP_DIR / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "retrievers_loaded": len(engines) > 0}


@app.get("/", response_class=FileResponse)
def serve_index():
    """Serve the Liquid Glass web interface."""
    index_file = APP_DIR / "static" / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="UI index.html not found")
    resp = FileResponse(index_file)
    # Prevent Electron/browser caching stale HTML between app updates
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    return resp


@app.get("/manifest.json", response_class=FileResponse)
def serve_manifest():
    """Serve PWA Web App Manifest."""
    manifest_file = APP_DIR / "static" / "manifest.json"
    if not manifest_file.exists():
        raise HTTPException(status_code=404, detail="manifest.json not found")
    return FileResponse(manifest_file, media_type="application/manifest+json")


@app.get("/service-worker.js", response_class=FileResponse)
def serve_service_worker():
    """Serve PWA Service Worker."""
    sw_file = APP_DIR / "static" / "service-worker.js"
    if not sw_file.exists():
        raise HTTPException(status_code=404, detail="service-worker.js not found")
    return FileResponse(sw_file, media_type="application/javascript")


@app.get("/favicon.ico", response_class=FileResponse)
def serve_favicon():
    """Serve app favicon."""
    fav_file = APP_DIR / "static" / "favicon.ico"
    if not fav_file.exists():
        raise HTTPException(status_code=404, detail="favicon.ico not found")
    return FileResponse(fav_file, media_type="image/x-icon")


downloads_dir = APP_DIR / "static" / "downloads"
downloads_dir.mkdir(parents=True, exist_ok=True)


@app.get("/downloads/{filename}", response_class=FileResponse)
def download_file(filename: str):
    """Serve downloadable desktop app binaries."""
    file_path = downloads_dir / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File {filename} not found")
    return FileResponse(file_path, filename=filename)


@app.get("/api/config", response_model=ConfigResponse)
def get_config():
    """Return configured methods, categories, thresholds, and Groq status."""
    fallback_router.reload_thresholds()
    groq_enabled = bool(polisher and polisher.is_available())

    methods = [
        MethodInfo(id="auto", name="Auto (Smart)", desc="Picks Hybrid, Semantic, or Keyword based on your question"),
        MethodInfo(id="hyb", name="Hybrid Fusion", desc="Weighted combination of lexical and dense retrieval (alpha=0.70)"),
        MethodInfo(id="emb", name="Semantic Embeddings", desc="Dense semantic vector matching using all-MiniLM-L6-v2"),
        MethodInfo(id="tf", name="TF-IDF Cosine", desc="Sublinear TF-IDF term weighting with cosine similarity"),
        MethodInfo(id="kw", name="Keyword Overlap", desc="Exact word overlap and Hinglish campus token mapping"),
    ]

    return ConfigResponse(
        thresholds=fallback_router.thresholds,
        methods=methods,
        categories=CATEGORIES,
        groq_enabled=groq_enabled,
    )


@app.post("/api/query", response_model=QueryResponse)
def handle_query(req: QueryRequest):
    """Handle student query with input validation, PII redaction, retrieval, threshold gating, and fallback routing."""
    start_time = time.perf_counter()

    raw_query = req.query.strip()
    # Guardrail 1: Control character stripping
    cleaned_query = re.sub(r"[\x00-\x1f\x7f-\x9f]", " ", raw_query).strip()
    if not cleaned_query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    if len(cleaned_query) > 300:
        raise HTTPException(status_code=400, detail="Query exceeds maximum length of 300 characters")

    # Guardrail 2: PII Redaction
    sanitized_query, _ = redact_pii(cleaned_query)

    # Auto-mode: pick method based on query characteristics
    requested_method = req.method.lower()
    auto_method_chosen = None
    if requested_method == "auto":
        auto_method_chosen = auto_select_method(sanitized_query)
        method_code = auto_method_chosen
    else:
        method_code = METHOD_NORMALIZATION.get(requested_method, "hyb")

    retriever = engines.get(method_code, engines.get("hyb"))
    if not retriever:
        raise HTTPException(status_code=500, detail="Retrieval engine not initialized")

    category_filter = req.category if req.category in CATEGORIES else "All"

    # Query retriever
    top_candidates = retriever.query(sanitized_query, top_k=3, category=category_filter)

    top_score = top_candidates[0]["score"] if top_candidates else 0.0
    active_threshold = fallback_router.get_threshold(method_code)
    is_fallback = fallback_router.should_fallback(top_score, method_code)

    matched_faq = None
    answer_original = None
    answer_polished = None
    polished = False
    ai_generated = False
    matched_faq_id = None
    groq_latency_ms = None
    groq_failed = False

    if not is_fallback and top_candidates:
        # ── Engine matched successfully ──────────────────────────────────────
        top_cand = top_candidates[0]
        matched_faq_id = top_cand["id"]
        matched_faq = MatchedFaq(
            id=top_cand["id"],
            question=top_cand["question"],
            category=top_cand["category"]
        )
        answer_original = top_cand["answer"]
        department_contact = top_cand.get("department_contact") or fallback_router.get_department_contact(top_cand["category"])

        # Grounded Groq Polish Layer
        if req.polish and polisher and polisher.is_available():
            raw_polished, groq_ok, groq_lat, msg = polisher.polish(
                query=sanitized_query,
                faq_id=matched_faq_id,
                answer_original=answer_original
            )
            groq_latency_ms = groq_lat
            if groq_ok:
                grounding_passed, ground_reason, _ = verify_grounding(answer_original, raw_polished)
                if grounding_passed:
                    answer_polished = raw_polished
                    polished = True
                    groq_failed = False
                else:
                    answer_polished = None
                    polished = False
                    groq_failed = True
            else:
                answer_polished = None
                polished = False
                groq_failed = True if ("failed" in msg or "timeout" in msg) else False

    else:
        # ── Engine missed → try Groq direct AI answer ───────────────────────
        department_contact = fallback_router.get_department_contact(category_filter)

        if req.polish and polisher and polisher.is_available() and not polisher.is_adversarial(sanitized_query):
            context_snippets = [
                f"FAQ [{c['id']}]: {c['question']} -> {c.get('answer', '')}"
                for c in top_candidates[:3]
                if c.get("question") and c.get("answer")
            ]
            ai_answer, groq_ok, groq_lat, msg = polisher.direct_answer(
                query=sanitized_query,
                category=category_filter,
                context=context_snippets
            )
            groq_latency_ms = groq_lat
            if groq_ok and ai_answer:
                answer_original = ai_answer
                ai_generated = True
                # is_fallback remains True to record retrieval abstention in telemetry & API,
                # while ai_generated=True signals generative AI fallback to the client
                groq_failed = False
            else:
                groq_failed = True
        # If Groq unavailable or fails, is_fallback stays True (existing fallback card shown)

    latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

    # Log telemetry to SQLite
    query_id = log_query(
        query=sanitized_query,
        method=method_code,
        category_filter=category_filter,
        matched_faq_id=matched_faq_id,
        score=top_score,
        threshold_used=active_threshold,
        fallback=is_fallback,
        polished=polished,
        groq_latency_ms=groq_latency_ms,
        groq_failed=groq_failed,
        latency_ms=latency_ms,
    )

    # Prepare candidate top3 list for explainability
    top3_formatted = [
        {
            "id": c["id"],
            "question": c["question"],
            "score": round(c["score"], 4),
            "category": c.get("category", "")
        }
        for c in top_candidates[:3]
    ]

    return QueryResponse(
        query_id=query_id,
        fallback=is_fallback,
        ai_generated=ai_generated,
        confidence=round(top_score, 4),
        threshold=round(active_threshold, 4),
        method=method_code,
        auto_method=auto_method_chosen,
        matched_faq=matched_faq,
        answer_original=answer_original,
        answer_polished=answer_polished,
        polished=polished,
        department_contact=department_contact,
        top3=top3_formatted,
        latency_ms=latency_ms,
    )


@app.post("/api/feedback", response_model=FeedbackResponse)
def handle_feedback(req: FeedbackRequest):
    """Record student feedback (thumbs-up / thumbs-down) for a specific query ID."""
    success = record_feedback(query_id=req.query_id, helpful=req.helpful)
    if not success:
        raise HTTPException(status_code=404, detail=f"Query ID {req.query_id} not found")
    return FeedbackResponse(status="ok")


@app.get("/api/analytics")
def handle_analytics():
    """Return aggregated query logs, confidence metrics, and fallback stats."""
    return get_analytics()


@app.get("/api/evaluation")
def handle_evaluation():
    """Return offline evaluation benchmark results and metrics from results/metrics.json."""
    if not METRICS_PATH.exists():
        raise HTTPException(status_code=404, detail="Evaluation results not yet generated. Run evaluate.py first.")
    with open(METRICS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Attach sample failure cases for viva defense error analysis
    failure_cases = []
    if FAILURE_CASES_PATH.exists():
        import csv
        with open(FAILURE_CASES_PATH, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            failure_cases = list(reader)[:15]

    data["failure_cases"] = failure_cases
    return data
