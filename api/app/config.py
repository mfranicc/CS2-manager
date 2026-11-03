from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Postavke aplikacije; vrijednosti se citaju iz varijabli okoline ili datoteke .env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    test_database_url: str | None = None
    secret_key: str
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7


settings = Settings()
