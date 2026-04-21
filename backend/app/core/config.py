from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database — defaults to SQLite for local dev; Sodiq wires Postgres URL in prod
    database_url: str = "sqlite+aiosqlite:///./litigation.db"

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    # Clerk — John/Sodiq will wire this when auth is bolted on
    clerk_jwks_url: str = ""

    # CORS — comma-separated origins or JSON array via env
    allowed_origins: list[str] = ["http://localhost:3000"]


settings = Settings()
