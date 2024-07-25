import jwt
import smtplib

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from .config import settings
from .security import verify_password, refresh_access_token
from ..db.models import User
from ..crud import user as user_crud


def authenticate(db: Session, email: str, password: str) -> User:
    user = user_crud.get_user_by_email(db, email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"User with email '{email}' does not exist.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Password is incorrect.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def handle_token_refresh(refresh_token: str, db: Session) -> dict[str, str]:
    try:
        new_access_token, new_refresh_token = refresh_access_token(
            refresh_token=refresh_token, db=db
        )
        return {
            "access_token": new_access_token,
            "access_token_expires_in_minutes": settings.access_token_expire_minutes,
            "refresh_token": new_refresh_token,
            "refresh_token_expires_in_days": settings.refresh_token_expire_days,
            "token_type": "bearer",
        }
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials, might be missing, invalid or expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred while refreshing token: {e}",
        )
