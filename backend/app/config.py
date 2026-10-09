"""Settings read from environment variables (and backend/.env when present)."""

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")

DEFAULT_GEMINI_MODEL = "gemini-3.5-flash-lite"
DEFAULT_CORS_ORIGINS = "http://localhost:3000,http://127.0.0.1:3000"


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str
    gemini_model: str
    cors_origins: list[str]


@lru_cache
def get_settings() -> Settings:
    origins = os.getenv("CORS_ORIGINS") or DEFAULT_CORS_ORIGINS
    return Settings(
        gemini_api_key=os.getenv("GEMINI_API_KEY", "").strip(),
        gemini_model=os.getenv("GEMINI_MODEL", "").strip() or DEFAULT_GEMINI_MODEL,
        cors_origins=[origin.strip().rstrip("/") for origin in origins.split(",") if origin.strip()],
    )
