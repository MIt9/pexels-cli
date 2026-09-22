"""Configuration management for Pexels CLI."""

import json
from pathlib import Path
from typing import Literal, Optional
from platformdirs import user_config_dir
from pydantic import BaseModel, Field


APP_NAME = "pexels-cli"
CONFIG_DIR = Path(user_config_dir(APP_NAME))
CONFIG_FILE = CONFIG_DIR / "config.json"


AIProvider = Literal["gemini", "openai", "ollama", "none"]


class Config(BaseModel):
    """Pexels CLI user configuration schema."""
    pexels_api_key: Optional[str] = Field(default=None, description="Pexels API Key")
    ai_provider: AIProvider = Field(default="gemini", description="Selected AI provider")
    gemini_api_key: Optional[str] = Field(default=None, description="Google Gemini API Key")
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API Key")
    openai_base_url: Optional[str] = Field(default=None, description="OpenAI Base URL (e.g. for vLLM/Groq)")
    ollama_host: str = Field(default="http://localhost:11434", description="Ollama API Host")
    ollama_model: str = Field(default="llama3.2", description="Ollama Model Name")
    gemini_model: str = Field(default="gemini-2.5-flash", description="Gemini Model Name")
    openai_model: str = Field(default="gpt-4o-mini", description="OpenAI Model Name")
    default_output: Literal["rich", "json"] = Field(default="rich", description="Default CLI output format")
    download_dir: str = Field(default="./downloads", description="Default download directory")


def load_config() -> Config:
    """Load configuration from file or environment fallback."""
    import os

    config_dict = {}
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config_dict = json.load(f)
        except Exception:
            pass

    config = Config(**config_dict)

    # Environment variable fallbacks (env vars override file config if set)
    if os.getenv("PEXELS_API_KEY"):
        config.pexels_api_key = os.getenv("PEXELS_API_KEY")
    if os.getenv("GEMINI_API_KEY"):
        config.gemini_api_key = os.getenv("GEMINI_API_KEY")
    if os.getenv("OPENAI_API_KEY"):
        config.openai_api_key = os.getenv("OPENAI_API_KEY")
    if os.getenv("OLLAMA_HOST"):
        config.ollama_host = os.getenv("OLLAMA_HOST")
    if os.getenv("PX_OUTPUT_FORMAT"):
        val = os.getenv("PX_OUTPUT_FORMAT", "").lower()
        if val in ("json", "rich"):
            config.default_output = val  # type: ignore

    return config


def save_config(config: Config) -> None:
    """Save configuration to disk."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config.model_dump(), f, indent=2, ensure_ascii=False)


def get_config_path() -> Path:
    """Return path to config file."""
    return CONFIG_FILE
