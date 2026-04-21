import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

BASE_DIR = Path(__file__).resolve().parent


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    DATABASE_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "database" / "faqcanvas.db"))
    DEMO_DATA_ENABLED = os.getenv("DEMO_DATA_ENABLED", "true").lower() == "true"
