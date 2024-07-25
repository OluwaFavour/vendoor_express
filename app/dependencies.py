import datetime

from fastapi import Depends, HTTPException, status
import jwt
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from typing import Optional, Annotated, Any

from .crud import token as token_crud
from .crud import user as user_crud
from .db.session import SessionLocal
from .db.models import User
from .core.config import oauth2_scheme, settings
from .core.debug import logger


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
        detail="Could not validate credentials, might be missing, invalid or expired",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload: dict[str, Any] = jwt.decode(
            jwt=token,
            key=settings.secret_key,
            algorithms=[settings.algorithm],
        )
        jti = payload.get("jti")
        if jti is None:
            raise credentials_exception
        email = payload.get("sub")
        if email is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
    user = user_crud.get_user_by_email(db, email)
    if user is None:
        raise credentials_exception

    # Check the token in the database
    db_token = token_crud.get_token(db, jti)
    if db_token is None:
        raise credentials_exception
    if db_token.expires_at.replace(tzinfo=datetime.UTC) < datetime.datetime.now(
        datetime.UTC
    ):
        try:
            token_crud.delete_token(db, jti)
        except SQLAlchemyError as e:
            logger.error(f"Could not delete token: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"message": "Could not delete token", "error": str(e)},
            )
        raise credentials_exception

    user = user_crud.get_user(db, db_token.user_id)
    if user is None:
        raise credentials_exception
    return user


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