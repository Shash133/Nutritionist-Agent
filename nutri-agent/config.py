"""Application configuration via pydantic-settings."""

import sys
from pathlib import Path

from pydantic_settings import BaseSettings
from pydantic import AliasChoices, Field


class Settings(BaseSettings):
    # ── Neo4j ────────────────────────────────────────────────────────────────
    neo4j_uri: str = Field(default="bolt://localhost:7687")
    # Aura's downloaded credentials file uses NEO4J_USERNAME
    neo4j_user: str = Field(
        default="neo4j",
        validation_alias=AliasChoices("neo4j_user", "neo4j_username"),
    )
    neo4j_password: str = Field(default="password")

    # ── LLM ──────────────────────────────────────────────────────────────────
    google_api_key: str = Field(default="")
    gemini_model: str = Field(default="gemini-3.8-flash")
    # Client-side throttle, shared across all replan calls in the process.
    # Set to your API tier's requests-per-minute limit.
    gemini_rpm: float = Field(default=10, gt=0)
    # Retries (exponential backoff) on 429 / 5xx from the Gemini API.
    gemini_max_retries: int = Field(default=6, ge=0)

    # ── App ──────────────────────────────────────────────────────────────────
    log_level: str = Field(default="INFO")
    max_replan_iterations: int = Field(default=3)
    embedding_model: str = Field(default="all-MiniLM-L6-v2")


    # Ignore unrelated keys (e.g. AURA_INSTANCEID) pasted from Aura's env file
    # .env is resolved next to this file so the app works from any working directory
    model_config = {
        "env_file": Path(__file__).resolve().parent / ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()


def configure_utf8_stdio() -> None:
    """
    Force UTF-8 on stdout/stderr. On Windows, redirected output defaults to
    cp1252, and log lines containing e.g. '→' or LLM text crash with
    UnicodeEncodeError. Call once from each entry point.
    """
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
