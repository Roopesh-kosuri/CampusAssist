"""Base abstract interface for all CampusAssist retrieval engines."""
from abc import ABC, abstractmethod


class BaseRetriever(ABC):
    """Abstract Base Class for campus FAQ retrieval models."""

    def __init__(self, method_name: str, method_code: str):
        self.method_name = method_name
        self.method_code = method_code
        self.faqs: list[dict] = []

    @abstractmethod
    def fit(self, faqs: list[dict]) -> None:
        """Index the provided FAQ knowledge base."""
        pass

    @abstractmethod
    def query(self, text: str, top_k: int = 3, category: str = "All") -> list[dict]:
        """Retrieve top_k matching FAQs for the given query.
        
        Args:
            text: Raw user query string.
            top_k: Number of candidate results to return (default: 3).
            category: Domain filter ("All", "Hostel", "Library", etc.).
            
        Returns:
            list[dict]: Ranked list of candidate FAQ dictionaries, each containing:
                - id (str): Canonical FAQ ID
                - question (str): Canonical question text
                - answer (str): FAQ answer
                - category (str): Domain category
                - department_contact (str): Helpdesk contact
                - score (float): Clamped similarity score in [0.0, 1.0]
        """
        pass

    def _filter_faqs(self, category: str = "All") -> list[dict]:
        """Filter indexed FAQs by category."""
        if category == "All" or not category:
            return self.faqs
        return [f for f in self.faqs if f.get("category") == category]
