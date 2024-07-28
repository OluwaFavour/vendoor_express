from datetime import timedelta
import jwt
from smtplib import SMTP
from typing import Annotated, Any
import uuid
import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Header, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from ..dependencies import get_db, get_current_active_user, get_smtp
from ..crud.user import get_user_by_email, get_user, update_user
from ..crud.token import (
    delete_token,
    delete_tokens_by_type,
    delete_session,
)
from ..db.models import User as UserModel
from ..db.enums import TokenType
from ..schemas.auth import Token, TokenPayload, ResetPasswordRequest
from ..core.config import settings
from ..core.utils import (
    authenticate,
    handle_token_refresh,
    send_email,
    get_html_from_template,
    create_session,
    delete_session_by_user_id,
)
from ..core.security import (
    create_token,
    hash_password,
)
from ..core.debug import logger

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post(
    "/login",
    status_code=status.HTTP_200_OK,
    summary="Login to the application",
    responses={
        200: {
            "description": "Successfully logged in",
            "content": {
                "application/json": {"example": {"message": "Successfully logged in"}}
            },
        }
    },
)
def login(
    user: Annotated[UserModel, Depends(authenticate)],
    db: Annotated[Session, Depends(get_db)],
    request: Request,
):
    # Generate session ID
    session_id = str(uuid.uuid4())

    # Store session
    expires_at = settings.session_expire_days
    expiry = datetime.datetime.now(datetime.UTC) + timedelta(days=expires_at)
    data = str(user.id)
    session_id = create_session(db=db, id=session_id, data=data, expires_at=expiry)
    request.session["session_id"] = session_id

    # Delete old session ID if it exists
    if "session_id" in request.cookies:
        old_session_id = request.cookies["session_id"]
        delete_session(db, uuid.UUID(old_session_id))

    # Store new session ID in cookie
    response = JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Successfully logged in"},
    )
    response.set_cookie(
        key="session_id", value=session_id, expires=expiry, httponly=True
    )

    # Return response
    return response


# This endpoint is deprecated, use the /login endpoint instead
@router.post("/refresh", response_model=Token, deprecated=True, include_in_schema=False)
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
    summary="Logout from the application",
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
    db: Annotated[Session, Depends(get_db)],
    request: Request,
):
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
    response = JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Successfully logged out"},
    )
    delete_session(db, uuid.UUID(session_id))
    response.delete_cookie("session_id")
    return response


@router.post(
    "/logoutall",
    status_code=status.HTTP_200_OK,
    summary="Logout from all devices",
    responses={
        200: {
            "description": "Successfully logged out all devices",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Successfully logged out all devices, or rather, all sessions"
                    }
                }
            },
        }
    },
)
def logout_all(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[UserModel, Depends(get_current_active_user)],
):
    delete_session_by_user_id(db, str(user.id))
    return {"message": "Successfully logged out all devices, or rather, all sessions"}


@router.post(
    "/forgot-password",
    status_code=status.HTTP_200_OK,
    summary="Generate password reset link",
)
def forgot_password(
    email: TokenPayload,
    db: Annotated[Session, Depends(get_db)],
    smtp: Annotated[SMTP, Depends(get_smtp)],
):
    email = email.email
    user = get_user_by_email(db=db, email=email)
    if user:
        reset_token_expires = timedelta(minutes=settings.reset_token_expire_minutes)
        reset_token = create_token(
            data={"sub": str(user.id)},
            db=db,
            token_type=TokenType.RESET.value,
            expires_delta=reset_token_expires,
        )
        reset_link = f"{settings.frontend_password_reset_url}?token={reset_token}"
        plain_text = f"Click the link to reset your password: {reset_link}"
        html_text = get_html_from_template(
            template="password_reset.html",
            reset_link=reset_link,
            user_name=user.full_name,
        )
        send_email(
            smtp=smtp,
            subject="Vendoor Express: Password Reset Request",
            recipient=email,
            plain_text=plain_text,
            html_text=html_text,
            sender=settings.from_email,
        )
        return {"message": "Password reset link sent to your email"}
    return None


@router.post(
    "/reset-password", status_code=status.HTTP_200_OK, summary="Reset password"
)
def reset_password(
    new_password: ResetPasswordRequest,
    authorization: Annotated[str, Header(pattern="Bearer .*")],
    db: Annotated[Session, Depends(get_db)],
):
    try:
        token = authorization.split(" ")[1]
        payload: dict[str, Any] = jwt.decode(
            jwt=token,
            key=settings.secret_key,
            algorithms=[settings.algorithm],
        )
        user_id = payload.get("sub")
        jti = payload.get("jti")
        user = get_user(db, uuid.UUID(user_id))
        if user:
            hashed_password = hash_password(new_password.new_password)
            user = update_user(db, user, hashed_password=hashed_password)

            # Delete token
            delete_token(db, jti)
            # Delete all other reset tokens
            delete_tokens_by_type(db, user.id, TokenType.RESET.value)
            return {"message": "Password reset successful"}
    except IndexError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials, might be missing, invalid or expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
