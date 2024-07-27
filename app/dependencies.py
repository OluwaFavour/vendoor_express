import smtplib

from fastapi import Depends, HTTPException, status
import jwt
from sqlalchemy.orm import Session
from typing import Annotated


from .crud import user as user_crud
from .db.enums import TokenType
from .db.session import SessionLocal
from .db.models import User
from .core.config import oauth2_scheme, settings
from .core.debug import logger
from .core.security import validate_token


def get_smtp():
    """Manage the SMTP connection by creating a new connection for each request"""
    smtp = smtplib.SMTP(settings.smtp_host, settings.smtp_port)
    try:
        smtp.starttls()
        smtp.login(settings.smtp_login, settings.smtp_password)
    except smtplib.SMTPHeloError as e:
        logger.error(f"Could not start TLS: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Could not start TLS", "error": str(e)},
        )
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"Could not authenticate: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Could not authenticate", "error": str(e)},
        )
    try:
        yield smtp
    finally:
        smtp.quit()


def get_db():
    """Manage the database session by creating a new session for each request"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    db: Annotated[Session, Depends(get_db)],
    token: Annotated[str, Depends(oauth2_scheme)],
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials, might be missing, or invalid",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        user = validate_token(token=token, token_type=TokenType.ACCESS, db=db)
        return user
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials, might be expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except HTTPException:
        raise credentials_exception


def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    if current_user.is_active:
        return current_user
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This user is currently inactive",
        )
