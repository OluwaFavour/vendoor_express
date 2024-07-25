from datetime import timedelta
import jwt
from smtplib import SMTP
from typing import Annotated, Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, status, Header, Form
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import EmailStr
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..dependencies import get_db, get_current_active_user, get_smtp
from ..crud.user import get_user_by_email, get_user, update_user
from ..crud.token import invalidate_token, invalidate_all_user_access_tokens
from ..db.models import User as UserModel
from ..db.enums import TokenType
from ..schemas.auth import Token, RefreshTokenOut, TokenPayload, ResetPasswordRequest
from ..core.config import settings, oauth2_scheme
from ..core.utils import authenticate, handle_token_refresh, send_email
from ..core.security import (
    create_access_token,
    create_refresh_token,
    create_reset_token,
    hash_password,
)
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


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
def forgot_password(
    email: TokenPayload,
    db: Annotated[Session, Depends(get_db)],
    smtp: Annotated[SMTP, Depends(get_smtp)],
):
    email = email.email
    user = get_user_by_email(db=db, email=email)
    if user:
        reset_token = create_reset_token(data={"sub": str(user.id)}, db=db)
        reset_link = f"{settings.frontend_password_reset_url}?token={reset_token}"
        plain_text = f"Click the link to reset your password: {reset_link}"
        html_text = f"""<!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Password Reset</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    background-color: #f4f4f4;
                    margin: 0;
                    padding: 0;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                }}
                .email-container {{
                    background-color: #FFFFFF;
                    padding: 20px;
                    border-radius: 10px;
                    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
                    text-align: center;
                    max-width: 600px;
                    width: 100%;
                }}
                .email-header img {{
                    width: 100px;
                }}
                .email-header h1 {{
                    font-size: 24px;
                    color: #333;
                    margin: 20px 0;
                }}
                .email-body p {{
                    font-size: 16px;
                    color: #666;
                    margin: 10px 0;
                }}
                .email-body .highlight {{
                    color: #C52E05;
                    font-weight: bold;
                }}
                .reset-button {{
                    background-color: #C52E05;
                    color: #FFFFFF;
                    padding: 10px 20px;
                    text-decoration: none;
                    border-radius: 5px;
                    margin-top: 20px;
                    display: inline-block;
                }}
                .reset-button:hover {{
                    background-color: #a12504;
                }}
            </style>
        </head>
        <body>
            <div class="email-container">
                <div class="email-header">
                    <img src="https://via.placeholder.com/100" alt="Logo">
                    <h1>Reset Password</h1>
                </div>
                <div class="email-body">
                    <p>Hi there,</p>
                    <p>We received a request to reset the password for your account.</p>
                    <p>Please click the button below to reset your password:</p>
                    <a href="{reset_link}" class="reset-button">Verify</a>
                    <p>If you did not request a password reset, please ignore this email or reply to let us know. This password reset link is only valid for the next 60 minutes.</p>
                    <p>Thanks,</p>
                    <p>The Vendoor Express Team</p>
                </div>
            </div>
        </body>
        </html>
        """
        send_email(
            smtp=smtp,
            subject="Vendoor Express: Password Reset Request",
            recipient=email,
            plain_text=plain_text,
            html_text=html_text,
        )
        return {"message": "Password reset link sent to your email"}
    return None


@router.post("/reset-password", status_code=status.HTTP_200_OK)
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

            # Invalidate the reset token
            invalidate_token(
                db=db, token_jti=jti, token_type=TokenType.RESET_PASSWORD.value
            )
            # Invalidate old reset tokens
            invalidate_all_user_access_tokens(db, user, TokenType.RESET_PASSWORD.value)
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
