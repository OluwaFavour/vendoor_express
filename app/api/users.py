import datetime
import jwt
from smtplib import SMTP
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from ..dependencies import get_db, get_current_active_user, get_smtp
from ..crud.user import (
    create_user as db_create_user,
    get_user_by_email as db_get_user_by_email,
)
from ..db.models import User as UserModel
from ..schemas.user import UserCreate, User
from ..core.config import settings
from ..core.debug import logger
from ..core.security import hash_password
from ..core.utils import send_verification_email as send_verification_email_utility

router = APIRouter(prefix="/api/users", tags=["users"])


@router.post(
    "/",
    status_code=status.HTTP_200_OK,
    summary="Generate user token and send email verification link",
    description="Generate user token and send email verification link",
    responses={
        200: {
            "description": "Success",
            "content": {
                "application/json": {
                    "example": {"message": "Email verification link sent"}
                }
            },
        }
    },
)
def send_verification_email(
    user_scheme: UserCreate,
    db: Annotated[Session, Depends(get_db)],
    smtp: Annotated[SMTP, Depends(get_smtp)],
    request: Request,
) -> dict[str, str]:
    db_user = db_get_user_by_email(db, user_scheme.email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already in use",
        )
    response = send_verification_email_utility(user_scheme, smtp, request)
    return response


@router.get(
    "/verify-email",
    status_code=status.HTTP_308_PERMANENT_REDIRECT,
    summary="Verify user email",
    description="Verify user email, and redirect to frontend",
)
def verify_user_email(
    token: Annotated[str, Query(title="Token", description="The user token to verify")],
    db: Annotated[Session, Depends(get_db)],
):
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        email, salt, role, full_name = payload["sub"].split(":")
        db_user = db_get_user_by_email(db, email)
        if not db_user:
            db_user = UserModel(
                email=email, full_name=full_name, role=role, hashed_password=salt
            )
            db.add(db_user)
            db.commit()
            db.refresh(db_user)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already verified",
            )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token expired",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token",
        )
    return RedirectResponse(
        url=f"{settings.frontend_url}/email/verify",
        status_code=status.HTTP_308_PERMANENT_REDIRECT,
    )


@router.get("/me", response_model=User, status_code=status.HTTP_200_OK)
def read_users_me(
    current_user: Annotated[UserModel, Depends(get_current_active_user)]
) -> User:
    return current_user
