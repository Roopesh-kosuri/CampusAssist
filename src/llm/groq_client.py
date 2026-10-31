"""Groq LLM Client for CampusAssist Answer Polishing.

Provides an optional, strictly-grounded linguistic polishing layer that
rewrites matched canonical FAQ answers into friendly student-oriented
language while enforcing zero-hallucination and prompt-injection guardrails.
"""
import os
import re
import time
from collections import OrderedDict
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False


# Adversarial prompt-injection patterns
ADVERSARIAL_PATTERNS = [
    re.compile(r"ignore\s+(?:all\s+)?(?:previous\s+)?instructions", re.IGNORECASE),
    re.compile(r"system\s+prompt", re.IGNORECASE),
    re.compile(r"developer\s+mode", re.IGNORECASE),
    re.compile(r"jailbreak", re.IGNORECASE),
    re.compile(r"dan\s+mode", re.IGNORECASE),
    re.compile(r"waive\s+(?:all\s+)?(?:my\s+)?(?:fees?|dues?)", re.IGNORECASE),
    re.compile(r"forget\s+(?:all\s+)?rules", re.IGNORECASE),
    re.compile(r"bypass\s+security", re.IGNORECASE),
    re.compile(r"act\s+as\s+(?:dan|unfiltered|admin)", re.IGNORECASE),
]

SYSTEM_PROMPT = """You are a helpful campus assistant for Lovely Professional University (LPU) students.
Your task is to rewrite the provided canonical FAQ answer in a clear, friendly, and natural conversational tone (matching the student's English or Hinglish tone).

CRITICAL GROUNDING RULES:
1. Use ONLY the factual information in the provided FAQ Answer.
2. Do NOT add, infer, or hallucinate any numbers, dates, times, fee amounts, room/block numbers, phone numbers, email addresses, URLs, or campus policies.
3. You MUST PRESERVE all [bracketed placeholders] (such as [gate closing time], [hostel complaint portal], [accounts office]) EXACTLY as they appear, enclosed in square brackets. NEVER alter, remove, or fill in a placeholder.
4. Keep your response concise: 2 to 3 friendly sentences."""


class GroqPolisher:
    """Manages Groq LLM API calls with caching, timeouts, and adversarial guardrails."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        cache_size: int = 500
    ):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        self.model = model or os.environ.get("GROQ_MODEL", "qwen/qwen3.8-27b")
        self.cache_size = cache_size
        self._cache: OrderedDict[tuple[str, str], str] = OrderedDict()
        self.client = None

        if GROQ_AVAILABLE and self.api_key:
            try:
                self.client = Groq(api_key=self.api_key, timeout=6.0)
            except Exception:
                self.client = None

    def is_available(self) -> bool:
        """Check if Groq client is configured and available."""
        return self.client is not None

    def is_adversarial(self, query: str) -> bool:
        """Detect prompt-injection or jailbreak patterns in user query."""
        if not query:
            return False
        return any(pattern.search(query) for pattern in ADVERSARIAL_PATTERNS)

    def polish(
        self,
        query: str,
        faq_id: str,
        answer_original: str
    ) -> tuple[str, bool, float, str]:
        """Polish the original FAQ answer using Groq.

        Returns:
            tuple[str, bool, float, str]: (polished_text, success, latency_ms, message)
        """
        # Guardrail 1: Check client availability
        if not self.is_available():
            return answer_original, False, 0.0, "Groq client not available or API key not set"

        # Guardrail 2: Adversarial query detection
        if self.is_adversarial(query):
            return answer_original, False, 0.0, "Adversarial query detected; polish skipped for safety"

        # Guardrail 3: Check LRU cache
        norm_key = (query.strip().lower(), faq_id)
        if norm_key in self._cache:
            self._cache.move_to_end(norm_key)
            return self._cache[norm_key], True, 0.5, "Retrieved from cache"

        start_time = time.perf_counter()
        user_content = f"Student Question: {query}\nCanonical FAQ Answer: {answer_original}\n\nRewritten friendly answer:"

        # Call Groq with 1 retry on timeout / rate-limit
        last_error = ""
        for attempt in range(2):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_content}
                    ],
                    temperature=0.1,
                    max_tokens=180,
                )
                latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
                polished_text = response.choices[0].message.content.strip()

                if not polished_text:
                    return answer_original, False, latency_ms, "Groq returned empty response"

                # Store in LRU cache
                self._cache[norm_key] = polished_text
                if len(self._cache) > self.cache_size:
                    self._cache.popitem(last=False)

                return polished_text, True, latency_ms, "Success"

            except Exception as e:
                last_error = str(e)
                time.sleep(0.5)

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return answer_original, False, latency_ms, f"Groq call failed after retry: {last_error}"
