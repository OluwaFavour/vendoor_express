from datetime import datetime, timedelta
import jwt
from typing import Annotated, Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..dependencies import get_db, get_current_active_user
from ..internal.crud import delete_token, delete_user_tokens
from ..internal.models import User as UserModel
from ..internal.schemas import Token
from ..internal.settings import get_settings, oauth2_scheme
from ..internal.utils import authenticate, create_access_token
from ..logger import logger

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=Token)
def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)],
):
    user = authenticate(db, email=form_data.username, password=form_data.password)
    access_token_expires = timedelta(minutes=get_settings().access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.email}, db=db, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


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
def logout(token: Annotated[str, Depends(oauth2_scheme)]):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload: dict[str, Any] = jwt.decode(
            jwt=token,
            key=get_settings().secret_key,
            algorithms=[get_settings().algorithm],
        )
        jti = payload.get("jti")
        if jti is None:
            raise credentials_exception
        try:
            delete_token(jti)
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
        delete_user_tokens(db, user)
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
