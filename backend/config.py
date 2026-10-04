from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Google Gemini API
    gemini_api_key: str = ""
    # Available models: gemini-2.0-flash (fast, free tier), gemini-1.5-pro, gemini-1.5-flash
    gemini_model: str = "gemini-2.5-flash"

    # App settings
    app_title: str = "Lingua Partner"
    app_version: str = "1.0.0"

    # Comma-separated origins, e.g. "*" or "https://a.com,https://b.com"
    cors_origins: str = "*"

    # Conversation memory: max turns kept per session
    max_history_turns: int = 20

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }

    def get_cors_origins(self) -> list[str]:
        """Parse cors_origins string into a list."""
        return [v.strip() for v in self.cors_origins.split(",") if v.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
