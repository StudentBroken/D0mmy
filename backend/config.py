from functools import lru_cache
from pathlib import Path
from typing import Literal
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_CHROMA   = "./data/chroma"
_DEFAULT_SPRINTS  = "./data/sprints.json"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Google API — single key for all models and embeddings
    google_api_key: str = Field(default="", description="Google AI API key")

    # Model IDs — all via Google AI API (aistudio.google.com)
    heavy_model: str = "gemini-3.1-pro-preview"     # Gemini 3.1 Pro
    worker_model: str = "gemma-4-31b-it"             # Gemma 4 31B (parallel workers)
    daemon_model: str = "gemma-4-26b-a4b-it"         # Gemma 4 26B MoE ~4B active (routing / truncation)
    embedding_model: str = "gemini-embedding-001"    # Gemini Embedding

    # Project mode — controls whether hardware agents and BOM validation are active
    project_mode: Literal["software", "hardware+software"] = "software"

    # FastAPI
    backend_host: str = "127.0.0.1"
    backend_port: int = 8000

    # Target repo — path of the project D0mmy is currently working on.
    # Empty = D0mmy's own directory (default, self-hosted mode).
    target_repo: str = ""

    # ChromaDB — auto-derived to {target_repo}/.d0mmy/chroma when target_repo is set
    chroma_persist_dir: str = _DEFAULT_CHROMA

    # Sprints — auto-derived to {target_repo}/.d0mmy/sprints.json when target_repo is set
    sprints_path: str = _DEFAULT_SPRINTS

    # Logging
    log_level: str = "INFO"

    @field_validator("google_api_key")
    @classmethod
    def must_not_be_empty(cls, v: str) -> str:
        if not v:
            raise ValueError(
                "GOOGLE_API_KEY is not set. Run `python scripts/setup_keys.py`."
            )
        return v

    @model_validator(mode="after")
    def derive_project_paths(self) -> "Settings":
        """Auto-point data paths into {target_repo}/.d0mmy/ when target_repo is set
        and the user hasn't explicitly overridden the paths in .env."""
        if self.target_repo:
            d0mmy = Path(self.target_repo) / ".d0mmy"
            if self.chroma_persist_dir == _DEFAULT_CHROMA:
                self.chroma_persist_dir = str(d0mmy / "chroma")
            if self.sprints_path == _DEFAULT_SPRINTS:
                self.sprints_path = str(d0mmy / "sprints.json")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
