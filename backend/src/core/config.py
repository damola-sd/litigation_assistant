from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    database_url: str = "postgresql://postgres:postgres@localhost:5432/litigation"
    clerk_jwks_url: str = ""
    openai_api_key: str = ""
    anthropic_api_key: str = ""


settings = Settings()
