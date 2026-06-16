from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Ambiente
    app_env: str = "development"

    # Banco de dados
    database_url: str = "sqlite:///./gesto.db"
    database_direct_url: str = ""

    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7

    # Administrador Mestre do SaaS
    saas_admin_email: str = ""
    saas_admin_password_hash: str = ""

    # Frontend autorizado a consumir a API
    cors_origins: str = (
        "http://127.0.0.1:5500,"
        "http://localhost:5500"
    )

    # Stripe: será configurado posteriormente
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [
            origem.strip()
            for origem in self.cors_origins.split(",")
            if origem.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()