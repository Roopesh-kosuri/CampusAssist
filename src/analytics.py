"""SQLite Telemetry and Analytics Module for CampusAssist.

Provides persistent query logging, feedback tracking (thumbs up/down),
and real-time aggregate analytics according to Section 5.4.
"""
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from src.config import DB_PATH, DATA_DIR


def init_db(db_path: Path = DB_PATH) -> None:
    """Initialize the SQLite database and create the query_logs table if not exists."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS query_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                query TEXT NOT NULL,
                method TEXT NOT NULL,
                category_filter TEXT NOT NULL,
                matched_faq_id TEXT,
                score REAL NOT NULL,
                threshold_used REAL NOT NULL,
                fallback INTEGER NOT NULL,
                polished INTEGER NOT NULL,
                groq_latency_ms REAL,
                groq_failed INTEGER NOT NULL,
                latency_ms REAL NOT NULL,
                helpful INTEGER
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_query_logs_timestamp ON query_logs(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_query_logs_fallback ON query_logs(fallback)")
        conn.commit()


def log_query(
    query: str,
    method: str,
    category_filter: str,
    matched_faq_id: str | None,
    score: float,
    threshold_used: float,
    fallback: bool,
    polished: bool,
    groq_latency_ms: float | None,
    groq_failed: bool,
    latency_ms: float,
    db_path: Path = DB_PATH
) -> int:
    """Log an incoming user query and retrieval outcome.

    Returns:
        int: The auto-incremented query ID for feedback tracking.
    """
    init_db(db_path)
    now_utc = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO query_logs (
                timestamp, query, method, category_filter, matched_faq_id,
                score, threshold_used, fallback, polished,
                groq_latency_ms, groq_failed, latency_ms, helpful
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
            """,
            (
                now_utc,
                query,
                method,
                category_filter,
                matched_faq_id,
                float(score),
                float(threshold_used),
                1 if fallback else 0,
                1 if polished else 0,
                float(groq_latency_ms) if groq_latency_ms is not None else None,
                1 if groq_failed else 0,
                float(latency_ms),
            )
        )
        conn.commit()
        return int(cursor.lastrowid)


def record_feedback(query_id: int, helpful: bool, db_path: Path = DB_PATH) -> bool:
    """Update student thumbs-up/down feedback for a query.

    Returns:
        bool: True if row was found and updated, False otherwise.
    """
    init_db(db_path)
    val = 1 if helpful else 0
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE query_logs SET helpful = ? WHERE id = ?", (val, query_id))
        conn.commit()
        return cursor.rowcount > 0


def get_analytics(db_path: Path = DB_PATH) -> dict:
    """Fetch aggregated system analytics across all logged queries."""
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Total queries
        cursor.execute("SELECT COUNT(*) as total FROM query_logs")
        total_queries = cursor.fetchone()["total"]

        if total_queries == 0:
            return {
                "total_queries": 0,
                "fallback_rate": 0.0,
                "avg_confidence": 0.0,
                "helpful_percent": 0.0,
                "by_category": {
                    "Hostel": 0, "Library": 0, "Fees": 0, "ID Card": 0, "Transport": 0, "Exams": 0
                },
                "recent_fallbacks": []
            }

        # Fallback count
        cursor.execute("SELECT COUNT(*) as cnt FROM query_logs WHERE fallback = 1")
        fallbacks = cursor.fetchone()["cnt"]
        fallback_rate = round((fallbacks / total_queries) * 100.0, 1)

        # Average confidence (only for answered queries, or all non-fallback queries)
        cursor.execute("SELECT AVG(score) as avg_s FROM query_logs WHERE fallback = 0")
        row = cursor.fetchone()
        avg_score = row["avg_s"] if row["avg_s"] is not None else 0.0
        avg_confidence = round(float(avg_score) * 100.0, 1)

        # Helpful percentage (of queries that received feedback)
        cursor.execute("SELECT COUNT(*) as rated, SUM(helpful) as helpful_cnt FROM query_logs WHERE helpful IS NOT NULL")
        row = cursor.fetchone()
        rated = row["rated"]
        helpful_cnt = row["helpful_cnt"] or 0
        helpful_percent = round((helpful_cnt / rated) * 100.0, 1) if rated > 0 else 0.0

        # Breakdown by category
        cursor.execute("""
            SELECT category_filter, COUNT(*) as cnt 
            FROM query_logs 
            GROUP BY category_filter
        """)
        cats_db = {r["category_filter"]: r["cnt"] for r in cursor.fetchall()}
        by_category = {
            "Hostel": cats_db.get("Hostel", 0),
            "Library": cats_db.get("Library", 0),
            "Fees": cats_db.get("Fees", 0),
            "ID Card": cats_db.get("ID Card", 0),
            "Transport": cats_db.get("Transport", 0),
            "Exams": cats_db.get("Exams", 0),
        }
        # If queries had "All", categorize based on matched_faq_id prefix if available
        cursor.execute("""
            SELECT matched_faq_id, COUNT(*) as cnt 
            FROM query_logs 
            WHERE category_filter = 'All' AND matched_faq_id IS NOT NULL 
            GROUP BY matched_faq_id
        """)
        for r in cursor.fetchall():
            prefix = r["matched_faq_id"].split("_")[0]
            cat_name = {
                "hos": "Hostel", "lib": "Library", "fee": "Fees",
                "idc": "ID Card", "trn": "Transport", "exm": "Exams"
            }.get(prefix)
            if cat_name:
                by_category[cat_name] = by_category.get(cat_name, 0) + r["cnt"]

        # Recent fallbacks (up to 5 recent queries that abstained)
        cursor.execute("""
            SELECT query 
            FROM query_logs 
            WHERE fallback = 1 
            ORDER BY id DESC 
            LIMIT 5
        """)
        recent_fallbacks = [r["query"] for r in cursor.fetchall()]

        return {
            "total_queries": total_queries,
            "fallback_rate": fallback_rate,
            "avg_confidence": avg_confidence,
            "helpful_percent": helpful_percent,
            "by_category": by_category,
            "recent_fallbacks": recent_fallbacks
        }
