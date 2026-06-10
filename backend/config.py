"""Centralised settings via pydantic-settings. Loads from .env in backend/ directory."""

from pydantic_settings import BaseSettings
from pathlib import Path

# .env lives in the backend/ directory
_env_path = Path(__file__).resolve().parent / ".env"


class Settings(BaseSettings):
    groq_api_key: str = ""
    mcp_enabled: bool = True
    tavily_api_key: str = ""
    langsmith_api_key: str = ""
    langsmith_tracing: str = "true"
    langsmith_project: str = "atlas"

    model_config = {"env_file": str(_env_path), "env_file_encoding": "utf-8"}


settings = Settings()
