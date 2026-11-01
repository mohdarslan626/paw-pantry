
from functools import lru_cache
from typing import Annotated

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    # Database
    database_url: str

    # JWT Authentication
    jwt_secret_key: SecretStr
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Application
    environment: str = "development"
    cors_allowed_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    seed_on_startup: bool = True

    # Email / SMTP configuration
    smtp_host: str = "mailpit"
    smtp_port: int = 1025
    smtp_use_tls: bool = False
    smtp_from_email: str = "noreply@pawpantry.local"

    # Password recovery
    frontend_url: str = "http://localhost:5173"
    password_reset_token_expire_minutes: int = 15

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def _split_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [
                origin.strip()
                for origin in value.split(",")
                if origin.strip()
            ]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
