from functools import lru_cache

from cryptography.fernet import Fernet
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "KNMIET Connect"
    environment: str = "development"
    database_url: str = Field(
        default="postgresql+asyncpg://knmiet:knmiet@localhost:5432/knmiet_connect",
        alias="DATABASE_URL",
    )
    migration_database_url: str | None = Field(default=None, alias="MIGRATION_DATABASE_URL")
    jwt_secret_key: str = Field(default="change-me-in-production", alias="JWT_SECRET_KEY")
    totp_encryption_key: str = Field(alias="TOTP_ENCRYPTION_KEY")
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 15
    refresh_token_days: int = 7
    device_cookie_name: str = "device_registration_token"
    access_cookie_name: str = "access_token"
    refresh_cookie_name: str = "refresh_token"
    csrf_cookie_name: str = "csrf_token"
    csrf_header_name: str = "X-CSRF-Token"
    secure_cookies: bool = False
    https_enabled: bool = False
    totp_interval_seconds: int = 30
    totp_valid_window: int = 1
    cors_origins: list[str] = ["http://localhost:8080", "http://localhost:8000"]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", populate_by_name=True)

    @field_validator("totp_encryption_key")
    @classmethod
    def validate_totp_encryption_key(cls, value: str) -> str:
        try:
            Fernet(value.encode("ascii"))
        except (ValueError, TypeError) as exc:
            raise ValueError("TOTP_ENCRYPTION_KEY must be a valid Fernet key") from exc
        return value

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        if self.environment.lower() != "production":
            return self
        if self.jwt_secret_key == "change-me-in-production" or len(self.jwt_secret_key) < 32:
            raise ValueError("Production JWT_SECRET_KEY must be non-default and at least 32 characters")
        if not self.secure_cookies:
            raise ValueError("SECURE_COOKIES must be true in production")
        if not self.https_enabled:
            raise ValueError("HTTPS_ENABLED must be true in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
