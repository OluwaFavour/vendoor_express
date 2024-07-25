from functools import lru_cache
from typing import Optional

from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    reset_token_expire_minutes: int = 15
    token_url: str = "auth/login"
    smtp_host: str
    smtp_port: int
    smtp_login: str
    smtp_password: str
    frontend_url: str = "http://127.0.0.1:8000"
    from_email: Optional[str]
    allowed_origins: list[str]
    allowed_methods: list[str] = ["GET", "POST", "PUT", "PATCH", "DELETE"]
    allow_credentials: bool = True

    model_config = SettingsConfigDict(env_file=".env")


@lru_cache
def get_settings() -> Settings:
    """Get the settings instance"""
    return Settings()


settings = get_settings()

# Password hashing
password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=settings.token_url)
