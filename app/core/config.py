import cloudinary
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
    frontend_password_reset_url: str = "http://127.0.0.1:8000/"
    from_email: Optional[str]
    allowed_origins: list[str]
    allowed_methods: list[str] = ["GET", "POST", "PUT", "PATCH", "DELETE"]
    allow_credentials: bool = True
    cloudinary_url: str

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


# Cloudinary configuration parser
def cloudinary_config_parser(cloudinary_url: str) -> dict[str, str]:
    cloudinary_config = {}
    cloudinary_url = cloudinary_url.split("://")[1]
    cloudinary_config["cloud_name"] = cloudinary_url.split("@")[1].split(".")[0]
    cloudinary_config["api_key"] = cloudinary_url.split("@")[0].split(":")[0]
    cloudinary_config["api_secret"] = cloudinary_url.split("@")[0].split(":")[1]
    return cloudinary_config


# Cloudinary configuration
config_data = cloudinary_config_parser(settings.cloudinary_url)
config = cloudinary.config(
    cloud_name=config_data["cloud_name"],
    api_key=config_data["api_key"],
    api_secret=config_data["api_secret"],
    secret=True,
)
