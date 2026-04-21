from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    database_url: str = "sqlite+aiosqlite:///./litigation.db"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    clerk_jwks_url: str = ""
    allowed_origins: list[str] = ["http://localhost:3000"]


settings = Settings()
