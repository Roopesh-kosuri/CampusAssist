"""Vercel Serverless Function entry point for CampusAssist FastAPI app."""
import sys
from pathlib import Path

# Ensure root project directory is on Python path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.main import app
