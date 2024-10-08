import datetime
import smtplib
from typing import Annotated
import uuid

from fastapi import Depends, HTTPException, status
from fastapi.requests import Request
from sqlalchemy.orm import Session
from twilio.rest import Client

from .core.config import settings
from .core.debug import logger
from .core.paystack import Paystack
from .crud import session as session_crud, user as user_crud
from .db.enums import UserRoleType, VendorStatusType
from .db.models import User
from .db.session import SessionLocal


def get_paystack_client():
    """Manage the Paystack client by creating a new client for each request"""
    paystack_client = Paystack()
    try:
        yield paystack_client
    finally:
        pass


def get_twilio_client():
    """Manage the Twilio client by creating a new client for each request"""
    twilio_client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
    try:
        yield twilio_client
    finally:
        pass


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


def get_current_user(db: Annotated[Session, Depends(get_db)], request: Request) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
    session_id = request.cookies.get("session_id")
    if session_id is None:
        raise credentials_exception
    session = session_crud.get_session(db, uuid.UUID(session_id))
    if session is None:
        raise credentials_exception
    if session.expires_at.replace(tzinfo=datetime.UTC) < datetime.datetime.now(
        datetime.UTC
    ):
        session_crud.delete_session(db, session.id)
        raise credentials_exception
    user_id = uuid.UUID(session.user_id)
    user = user_crud.get_user(db, user_id)
    if user is None:
        session_crud.delete_session(db, session.id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found. The user associated with this session has probably been deleted.",
        )
    return user


def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    if current_user.is_active:
        return current_user
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This user is currently inactive",
        )


def get_current_active_admin(
    current_user: Annotated[User, Depends(get_current_active_user)]
) -> User:
    if current_user.role == "admin":
        return current_user
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This user does not have the necessary permissions to access this resource",
        )


def get_current_active_vendor(
    current_user: Annotated[User, Depends(get_current_active_user)]
) -> User:
    if (
        current_user.role == UserRoleType.VENDOR.value
        or current_user.role == UserRoleType.ADMIN.value
    ):
        return current_user
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": "This user does not have the necessary permissions to access this resource",
                "role": current_user.role,
            },
        )


def get_current_active_verified_vendor(
    current_vendor: Annotated[User, Depends(get_current_active_vendor)]
) -> User:
    if (
        current_vendor.shop.status == VendorStatusType.VERIFIED.value
        or current_vendor.role == UserRoleType.ADMIN.value
    ):
        return current_vendor
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": "This vendor has not been verified, please contact support",
                "status": current_vendor.shop.status,
            },
        )
