from datetime import timedelta
import jwt
from smtplib import SMTP
from typing import Annotated, Any
import uuid
import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Header, Request
from fastapi.responses import JSONResponse
from pydantic import EmailStr
from sqlalchemy.orm import Session

from ..dependencies import get_db, get_current_active_user, get_smtp
from ..crud.user import get_user_by_email, get_user, update_user
from ..crud.session import (
    delete_session,
)
from ..db.models import User as UserModel
from ..schemas.auth import ResetPasswordRequest, EmailPayload
from ..core.config import settings
from ..core.utils import (
    authenticate,
    send_email,
    get_html_from_template,
    create_session,
    delete_session_by_user_id,
)
from ..core.security import (
    hash_password,
)

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
    # Get session data
    data = str(user.id)

    # Delete old session IDs if they exists
    delete_session_by_user_id(db, data)
    if "session_id" in request.cookies:
        old_session_id = request.cookies["session_id"]
        delete_session(db, uuid.UUID(old_session_id))

    # Get user agent and IP address
    user_agent = request.headers.get("User-Agent")
    ip_address = request.client.host

    # Generate session ID
    session_id = str(uuid.uuid4())
    # Store session
    expires_at = settings.session_expire_days
    expiry = datetime.datetime.now(datetime.UTC) + timedelta(days=expires_at)
    session_id = create_session(
        db=db,
        id=session_id,
        data=data,
        expires_at=expiry,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    request.session["session_id"] = session_id

    # Update user's first login status
    if user.is_first_login is None:
        update_user(db, user, is_first_login=True)
    else:
        update_user(db, user, is_first_login=False)

    # Create response
    response = JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "Successfully logged in",
            "user_agent": user_agent,
            "ip_address": ip_address,
            "is_first_login": user.is_first_login,
        },
    )
    # Store new session ID in cookie
    response.set_cookie(
        key=settings.session_cookie_name,
        value=session_id,
        httponly=True,
        samesite=settings.same_site,
        max_age=(expires_at * 24 * 60 * 60),
        secure=settings.https_only,
    )

    # Return response
    return response


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
    email: EmailPayload,
    db: Annotated[Session, Depends(get_db)],
    smtp: Annotated[SMTP, Depends(get_smtp)],
):
    email = email.email
    user = get_user_by_email(db=db, email=email)
    if user:
        expire = datetime.datetime.now(datetime.UTC) + datetime.timedelta(
            minutes=settings.reset_token_expire_minutes
        )
        data = {"sub": str(user.id), "exp": expire}
        to_encode = data.copy()
        reset_token = jwt.encode(
            to_encode, settings.secret_key, algorithm=settings.algorithm
        )
        reset_link = f"{settings.frontend_url}/reset-password?token={reset_token}"
        plain_text = f"Click the link to reset your password: {reset_link}"
        html_text = get_html_from_template(
            template="password_reset.html",
            reset_link=reset_link,
            user_name=user.full_name,
            reset_link_expiry=settings.reset_token_expire_minutes,
        )
        send_email(
            smtp=smtp,
            subject="Vendoor Express - Password Reset Request",
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
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        user_id = uuid.UUID(payload.get("sub"))
        user = get_user(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        hashed_password = hash_password(new_password.new_password)
        user = update_user(db, user, hashed_password=hashed_password)
        return {"message": "Password reset successful"}
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials, token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
