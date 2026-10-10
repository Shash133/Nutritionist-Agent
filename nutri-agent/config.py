"""Application configuration via pydantic-settings."""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # ── Neo4j ────────────────────────────────────────────────────────────────
    neo4j_uri: str = Field(default="bolt://localhost:7687")
    neo4j_user: str = Field(default="neo4j")
    neo4j_password: str = Field(default="password")

    # ── LLM ──────────────────────────────────────────────────────────────────
    google_api_key: str = Field(default="")
    gemini_model: str = Field(default="gemini-2.0-flash")

    # ── App ──────────────────────────────────────────────────────────────────
    log_level: str = Field(default="INFO")
    max_replan_iterations: int = Field(default=3)
    embedding_model: str = Field(default="all-MiniLM-L6-v2")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
