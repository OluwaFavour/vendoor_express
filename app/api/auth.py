from datetime import timedelta
import jwt
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..dependencies import get_db, get_current_active_user
from ..crud.token import invalidate_token, invalidate_all_user_access_tokens
from ..db.models import User as UserModel
from ..db.enums import TokenType
from ..schemas.auth import Token, RefreshTokenOut
from ..core.config import settings, oauth2_scheme
from ..core.utils import authenticate, handle_token_refresh
from ..core.security import create_access_token, create_refresh_token
from ..core.debug import logger

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=Token)
def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)],
):
    user = authenticate(db, email=form_data.username, password=form_data.password)
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    refresh_token_expires = timedelta(days=settings.refresh_token_expire_days)
    access_token = create_access_token(
        data={"sub": str(user.id)}, db=db, expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(
        data={"sub": str(user.id)}, db=db, expires_delta=refresh_token_expires
    )
    return {
        "access_token": access_token,
        "access_token_expires_in_minutes": settings.access_token_expire_minutes,
        "refresh_token": refresh_token,
        "refresh_token_expires_in_days": settings.refresh_token_expire_days,
        "token_type": "bearer",
    }


@router.post("/refresh", response_model=RefreshTokenOut)
def refresh_access_token(
    authorization: Annotated[str, Header(pattern="Bearer .*")],
    db: Annotated[Session, Depends(get_db)],
):
    try:
        refresh_token = authorization.split(" ")[1]
        return handle_token_refresh(refresh_token=refresh_token, db=db)
    except IndexError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(get_current_active_user)],
    responses={
        200: {
            "description": "Successfully logged out",
            "content": {
                "application/json": {"example": {"message": "Successfully logged out"}}
            },
        }
    },
)
def logout(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
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
        try:
            invalidate_token(db=db, token_jti=jti, token_type=TokenType.ACCESS.value)
        except SQLAlchemyError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "message": "Internal server error, an error occurred while logging out",
                    "error": str(e),
                },
            )
    except jwt.PyJWTError:
        raise credentials_exception
    return {"message": "Successfully logged out"}


@router.post(
    "/logoutall",
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Successfully logged out all devices",
            "content": {
                "application/json": {
                    "example": {"message": "Successfully logged out all devices"}
                }
            },
        }
    },
)
def logout_all(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[UserModel, Depends(get_current_active_user)],
):
    try:
        invalidate_all_user_access_tokens(db=db, user=user)
    except SQLAlchemyError as e:
        logger.error(f"Error deleting user tokens: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Internal server error, an error occurred while logging out all devices",
                "error": str(e),
            },
        )
    logger.info(f"User {user.id} logged out from all devices")
    return {"message": "Successfully logged out all devices"}
