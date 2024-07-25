import jwt
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from smtplib import (
    SMTP,
    SMTPRecipientsRefused,
    SMTPSenderRefused,
    SMTPDataError,
    SMTPException,
)
from typing import Optional, Union

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


def create_email_message(
    subject: str, recipient: str, plain_text: str, html_text: Optional[str] = None
) -> Union[MIMEText, MIMEMultipart]:
    if html_text:
        message = MIMEMultipart("alternative")
        message.attach(MIMEText(plain_text, "plain"))
        message.attach(MIMEText(html_text, "html"))
    else:
        message = MIMEText(plain_text, "plain")

    message["Subject"] = subject
    message["From"] = settings.from_email
    message["To"] = recipient

    return message


def send_email(
    smtp: SMTP, subject: str, recipient: str, plain_text: str, html_text: Optional[str]
) -> None:
    try:
        message = create_email_message(subject, recipient, plain_text, html_text)
        smtp.sendmail(settings.from_email, recipient, message.as_string())
    except SMTPRecipientsRefused as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Recipient refused", "error": str(e)},
        )
    except SMTPSenderRefused as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Sender refused", "error": str(e)},
        )
    except SMTPDataError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Data error", "error": str(e)},
        )
    except SMTPException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Internal server error when sending mail",
                "error": str(e),
            },
        )
    else:
        return None
