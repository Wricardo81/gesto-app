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

    # Stripe
    stripe_secret_key: str | None = None
    stripe_webhook_secret: str | None = None

    stripe_price_mensal: str | None = None
    stripe_price_trimestral: str | None = None
    stripe_price_anual: str | None = None

    # Mercado Pago
    mercado_pago_access_token: str | None = None
    mercado_pago_webhook_secret: str | None = None
    mercado_pago_notification_url: str | None = None

    # Frontend
    frontend_base_url: str = "http://127.0.0.1:5500/frontend"

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