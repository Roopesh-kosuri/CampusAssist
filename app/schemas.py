"""Pydantic request and response schemas for CampusAssist API."""
from pydantic import BaseModel, Field
from typing import Optional


class MethodInfo(BaseModel):
    id: str
    name: str
    desc: str


class ConfigResponse(BaseModel):
    thresholds: dict[str, float]
    methods: list[MethodInfo]
    categories: list[str]
    groq_enabled: bool


class QueryRequest(BaseModel):
    query: str = Field(..., max_length=300, description="Student question (max 300 chars)")
    method: str = Field(default="auto", description="Method code: kw, tf, emb, emb_kw, hyb, or auto")
    category: str = Field(default="All", description="Target category or 'All'")
    polish: bool = Field(default=True, description="Whether to request LLM polish if available")


class MatchedFaq(BaseModel):
    id: str
    question: str
    category: str


class Candidate(BaseModel):
    id: str
    question: str
    score: float
    category: Optional[str] = None


class QueryResponse(BaseModel):
    query_id: int
    fallback: bool
    ai_generated: bool = False   # True when answer came from direct Groq fallback
    confidence: float
    threshold: float
    method: str
    auto_method: Optional[str] = None  # populated when method=auto, shows chosen method
    matched_faq: Optional[MatchedFaq] = None
    answer_original: Optional[str] = None
    answer_polished: Optional[str] = None
    polished: bool
    department_contact: str
    top3: list[dict]
    latency_ms: float


class FeedbackRequest(BaseModel):
    query_id: int
    helpful: bool


class FeedbackResponse(BaseModel):
    status: str
