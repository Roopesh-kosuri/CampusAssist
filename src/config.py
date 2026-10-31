"""CampusAssist central configuration."""
from pathlib import Path

# Base Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RESULTS_DIR = PROJECT_ROOT / "results"
TESTS_DIR = PROJECT_ROOT / "tests"
APP_DIR = PROJECT_ROOT / "app"

# Data Files
FAQS_PATH = DATA_DIR / "faqs.json"
OWNER_FACTS_PATH = DATA_DIR / "owner_facts.md"
PARAPHRASES_PATH = DATA_DIR / "paraphrases.csv"
OUT_OF_SCOPE_PATH = DATA_DIR / "out_of_scope.csv"
DB_PATH = DATA_DIR / "query_logs.db"

# Results Files
METRICS_PATH = RESULTS_DIR / "metrics.json"
THRESHOLDS_PATH = RESULTS_DIR / "thresholds.json"
PER_TYPE_ACCURACY_PATH = RESULTS_DIR / "per_type_accuracy.csv"
FAILURE_CASES_PATH = RESULTS_DIR / "failure_cases.csv"
GROUNDING_REPORT_PATH = RESULTS_DIR / "grounding_report.csv"

# Models and Thresholds
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384

CATEGORIES = ["All", "Hostel", "Library", "Fees", "ID Card", "Transport", "Exams"]
VALID_CATEGORIES = {"Hostel", "Library", "Fees", "ID Card", "Transport", "Exams"}

CATEGORY_PREFIX_MAP = {
    "hos": "Hostel",
    "lib": "Library",
    "fee": "Fees",
    "idc": "ID Card",
    "trn": "Transport",
    "exm": "Exams"
}
PREFIX_CATEGORY_MAP = {v: k for k, v in CATEGORY_PREFIX_MAP.items()}
