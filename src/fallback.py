"""Confidence-based abstention and department routing module for CampusAssist.

Determines when the retrieval engine should abstain from answering and routes
students to the appropriate Lovely Professional University helpdesk.
"""
from src.config import THRESHOLDS_PATH
import json

# Canonical fallback contacts per domain category
DEFAULT_DEPARTMENT_CONTACTS = {
    "Hostel": "Hostel Warden Helpdesk (Ground Floor Warden Office, Respective Hostel Block)",
    "Library": "Central Library Helpdesk (Ground Floor Circulation Desk, Block 37/38)",
    "Fees": "Division of Student Accounts & Fees (Block 34, Ground Floor)",
    "ID Card": "Security & UID Office (Block 30 / Division of Student Affairs Block 34)",
    "Transport": "Transport Management Division (Central Bus Terminus Counter, Gate 4)",
    "Exams": "Office of the Controller of Examinations (Block 34, Administrative Wing)",
    "All": "LPU Central Student Welfare Facilitation Desk (Block 30 / Block 34) · RMS Portal on UMS"
}

DEFAULT_THRESHOLDS = {
    "kw": 0.40,
    "tf": 0.35,
    "emb": 0.50,
    "emb_kw": 0.50,
    "hyb": 0.45
}


class FallbackRouter:
    """Manages confidence thresholds and routing to campus support."""

    def __init__(self, thresholds: dict[str, float] | None = None):
        self.thresholds = dict(DEFAULT_THRESHOLDS)
        if thresholds:
            self.thresholds.update(thresholds)
        else:
            self.reload_thresholds()

    def reload_thresholds(self) -> None:
        """Reload calibrated thresholds from results/thresholds.json if present."""
        if THRESHOLDS_PATH.exists():
            try:
                with open(THRESHOLDS_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    loaded_th = data.get("thresholds", {})
                    self.thresholds.update(loaded_th)
            except Exception:
                pass

    def get_threshold(self, method_code: str) -> float:
        """Get the active confidence threshold for the specified method."""
        return self.thresholds.get(method_code, 0.50)

    def should_fallback(self, top_score: float, method_code: str) -> bool:
        """Check if top similarity score is below the active calibrated threshold."""
        tau = self.get_threshold(method_code)
        return top_score < tau

    def get_department_contact(self, category: str) -> str:
        """Get the official contact channel for a given campus category."""
        return DEFAULT_DEPARTMENT_CONTACTS.get(category, DEFAULT_DEPARTMENT_CONTACTS["All"])

    def create_fallback_payload(
        self,
        query: str,
        method_code: str,
        category: str,
        top_candidates: list[dict]
    ) -> dict:
        """Construct structured fallback payload when abstaining."""
        tau = self.get_threshold(method_code)
        top_score = top_candidates[0]["score"] if top_candidates else 0.0
        contact = self.get_department_contact(category)

        return {
            "query": query,
            "fallback": True,
            "confidence": top_score,
            "threshold": tau,
            "method": method_code,
            "category": category,
            "department_contact": contact,
            "answer_original": None,
            "answer_polished": None,
            "polished": False,
            "top3": top_candidates,
            "message": "I couldn't find a sufficiently close match in the campus FAQ. Please consult the department contact below."
        }
