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
2. Do NOT add, infer, or hallucinate any numbers, dates, times, fee amounts, room/block numbers, phone numbers, email addresses, URLs, or campus policies not present in the FAQ answer.
3. You MUST PRESERVE all official URLs, phone numbers, and block numbers (e.g., Block 32, Block 37, https://ums.lpu.in/lpuums/) from the original answer.
4. Keep your response concise: 2 to 3 friendly sentences."""

FALLBACK_SYSTEM_PROMPT = """You are CampusAssist, the official AI student helper for Lovely Professional University (LPU), Phagwara, Punjab.

Answer questions about LPU campus life, academic facilities, library, study areas, services, portals, and student procedures.
Be warm, helpful, and concise (2-4 sentences), matching the student's tone (English or Hinglish).

VERIFIED LPU CAMPUS FACTS & PATHWAYS:

1. EXACT UMS (University Management System) PORTAL PATHWAYS:
- Examination Seating Plan & Room: UMS (https://ums.lpu.in/lpuums/) → Examination → Seating Plan → Select Course Code → View Allotted Block, Room Number, & Bench (released on UMS 1–2 hours or the evening prior to the exam shift).
- Date Sheet: UMS → Examination → Date Sheet or e-Connect (https://econnect.lpu.in) → Exam Connect → Date Sheet.
- Admit Card / Hall Ticket: UMS → Examination → Admit Card → Download & Print Hard Copy (requires 75% attendance; must carry printed copy + LPU ID card).
- CA Marks & Attendance: UMS → Continuous Assessment (CA) / Academic Tasks → View Marks/Rubrics, and UMS → Attendance → View Aggregate (mandatory 75% aggregate to sit for End-Term Exams).
- Grades & Results: UMS → Examination → Grade Card / Result or e-Connect → Exam Connect → Term Result.
- Hostel Leave & Gate Pass: UMS → Hostel / Residential Services → Leave Management → Apply Leave (Home / Day-out / Night-out) → Parent SMS Approval → Biometric Turnstile clearance at hostel gate.
- Maintenance & Repairs (RMS): UMS → Relationship Management System (RMS) → Log Request → Select Category (Electrical / Plumbing / Carpenter / Wi-Fi) → Enter Block & Room → Submit Ticket.
- Fee Payment & Receipts: UMS → Fee Management → Make Online Payment or directly via Fee Portal (https://zee.lpu.in/feepayment/) → Fee Receipts → View & Download Official Tax Invoice.

2. RESIDENTIAL FACILITIES (BH & GH HOSTELS):
- Boys Hostels (BH): BH-1, BH-2, BH-3, BH-4, BH-5, BH-6, BH-7, BH-8, plus multi-story apartment complexes.
- Girls Hostels (GH): GH-1, GH-2, GH-3, GH-4, GH-5, GH-6.
- Room Configurations: Standard 1-seater, 2-seater, 3-seater, 4-seater (AC, Air-Cooler, or Non-AC), with attached or common washroom options.
- Room Amenities: Bed, mattress, study desk, chair, almirah, and 24x7 Wi-Fi (LPU_Campus).
- Hostel Infrastructure: Biometric turnstile gates, dedicated floor wardens, 24/7 CCTV security, centralized laundry basements (40 pieces/month quota), common study rooms, indoor games, and night canteens.

3. FOOD COURTS, DINING & CAFETERIAS:
- Uni-Mall Food Court (Central shopping hub near Block 13): Features Domino's Pizza, Subway, Baskin Robbins, Dosa Plaza, Chai Point, bakery, juice bars, and multi-cuisine stalls.
- Academic Food Hubs: Kiosks, Nescafe booths, and Maggi hotspots across Block 13 (Amphitheatre food zone), Block 34, and Block 38.
- Hostel Messes: North Indian Mess, South Indian Mess, and Special Mess serving 4 hygienic vegetarian meals daily (Breakfast, Lunch, Evening Snacks, Dinner).
- Night Canteens: Located inside BH and GH hostel complexes, operational until 12:00 AM – 1:00 AM for late-night study snacks, parathas, and hot beverages.

4. MAJOR ACADEMIC BLOCKS & CAMPUS HUBS:
- Block 13: Student Activity Centre, Open-Air Amphitheatre, Uni-Mall gateway, food courts, and student cultural clubs.
- Blocks 25 to 28: School of Computer Science & Engineering (CSE) and Core Engineering Labs.
- Block 29: School of Design, Fashion, Fine Arts, and Architecture.
- Block 30: Division of Student Welfare (DSW), Counseling, Cultural clubs, Sports Directorate.
- Block 32: Central Administrative Hub, Office of the Vice Chancellor, Registrar, Accounts, HR, Security, and Chief Warden.
- Block 34: Examination Division (Controller of Examinations - COE), Academic Affairs, Classrooms.
- Block 36: Mittal School of Business (MBA / BBA), Executive Seminar Halls.
- Block 37: Central Library (4 floors, open 8:00 AM – 12:00 AM midnight daily, extended to 2:00 AM during exams, quiet cubicles, discussion rooms).
- Block 38: Shanti Devi Mittal Auditorium, Central Server Room, Advanced Computing Labs.
- Uni-Hospital: 24/7 multi-specialty university hospital with resident doctors, trauma care, ambulance, and pharmacy near the main gate.
- Uni-Mall: Central student shopping mall with SBI/PNB bank branches, ATMs, post office, supermarkets, salons, stationery, and bowling/gaming alley.

5. OFFICIAL PORTALS & HELPLINES:
- UMS Portal: https://ums.lpu.in/lpuums/
- Fee Payment: https://zee.lpu.in/feepayment/
- e-Connect (Exams/Results): https://econnect.lpu.in
- Main Website: https://www.lpu.in
- Helplines: +91-1824-517000 | Toll-Free: 1800-102-4431

RULES:
1. Always synthesize a concrete, helpful answer for study spaces, facilities, or campus procedures. Include exact UMS breadcrumbs (e.g. UMS → Examination → Seating Plan) and block numbers when asked about navigation.
2. If reference campus information is provided, ground your answer directly in those facts.
3. If asked something completely unrelated to university or student life, politely state you only handle LPU queries and offer the helpline +91-1824-517000.
4. Keep answers friendly, practical, and under 4 sentences. Include relevant portal URLs or block numbers."""


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

    def direct_answer(
        self,
        query: str,
        category: str = "All",
        context: list[str] | None = None
    ) -> tuple[str, bool, float, str]:
        """Generate a direct AI answer when the retrieval engine fails (fallback mode).

        Unlike polish(), this is a generative call — it produces a full answer
        from the LPU knowledge baked into the LLM, grounded by reference context
        and the system prompt.

        Returns:
            tuple[str, bool, float, str]: (answer_text, success, latency_ms, message)
        """
        if not self.is_available():
            return "", False, 0.0, "Groq client not available"

        if self.is_adversarial(query):
            return "", False, 0.0, "Adversarial query detected; AI fallback skipped"

        # Cache keyed on query alone for fallback answers
        cache_key = ("__fallback__", query.strip().lower())
        if cache_key in self._cache:
            self._cache.move_to_end(cache_key)
            return self._cache[cache_key], True, 0.5, "Retrieved from cache"

        start_time = time.perf_counter()
        category_hint = f" The student is asking about: {category}." if category and category != "All" else ""

        if context:
            context_block = "\n".join(f"- {c}" for c in context[:3])
            user_content = (
                f"Relevant LPU Knowledge Base entries:\n{context_block}\n\n"
                f"Student question:{category_hint} {query}\n\n"
                "Provide a helpful, friendly, and accurate answer for the student based on LPU facts:"
            )
        else:
            user_content = f"Student question:{category_hint} {query}"

        last_error = ""
        for attempt in range(2):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": FALLBACK_SYSTEM_PROMPT},
                        {"role": "user", "content": user_content}
                    ],
                    temperature=0.2,
                    max_tokens=250,
                )
                latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
                answer = response.choices[0].message.content.strip()

                if not answer:
                    return "", False, latency_ms, "Empty response from Groq"

                # Cache the answer
                self._cache[cache_key] = answer
                if len(self._cache) > self.cache_size:
                    self._cache.popitem(last=False)

                return answer, True, latency_ms, "Success"

            except Exception as e:
                last_error = str(e)
                time.sleep(0.5)

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return "", False, latency_ms, f"Groq fallback failed: {last_error}"

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
