import uuid
import datetime
from jinja2 import FileSystemLoader, Environment
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from smtplib import (
    SMTP,
    SMTPRecipientsRefused,
    SMTPSenderRefused,
    SMTPDataError,
    SMTPException,
)
from typing import Optional, Union, Any, Annotated

from cloudinary.uploader import upload
from cloudinary.api import delete_resources_by_prefix, delete_folder
from fastapi import HTTPException, status, Depends
from sqlalchemy.orm import Session

from .config import settings
from .security import verify_password
from ..db.models import User
from ..crud import user as user_crud, token as token_crud
from ..forms.auth import LoginForm
from ..dependencies import get_db


def authenticate(
    db: Annotated[Session, Depends(get_db)],
    credentials: Annotated[LoginForm, Depends()],
) -> User:
    email = credentials.email
    password = credentials.password
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


def create_session(
    db: Annotated[Session, Depends(get_db)],
    id: str,
    data: str,
    user_agent: str,
    ip_address: str,
    expires_at: datetime.datetime,
) -> str:
    session = token_crud.store_session(
        db=db,
        session_id=uuid.UUID(id),
        data=data,
        expires_at=expires_at,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    return str(session.id)


def delete_session_by_user_id(
    db: Annotated[Session, Depends(get_db)], user_id: str
) -> None:
    token_crud.delete_session_by_user_id(db, user_id)


def create_email_message(
    subject: str,
    recipient: str,
    plain_text: str,
    sender: str,
    html_text: Optional[str] = None,
) -> Union[MIMEText, MIMEMultipart]:
    if html_text:
        message = MIMEMultipart("alternative")
        message.attach(MIMEText(plain_text, "plain"))
        message.attach(MIMEText(html_text, "html"))
    else:
        message = MIMEText(plain_text, "plain")

    message["Subject"] = subject
    message["From"] = sender
    message["To"] = recipient

    return message


def send_email(
    smtp: SMTP,
    subject: str,
    recipient: str,
    plain_text: str,
    html_text: Optional[str] = None,
    sender: str = settings.from_email,
) -> None:
    try:
        message = create_email_message(
            subject=subject,
            recipient=recipient,
            plain_text=plain_text,
            html_text=html_text,
            sender=sender,
        )
        smtp.sendmail(sender, recipient, message.as_string())
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


def get_html_from_template(template: str, **kwargs) -> str:
    env = Environment(loader=FileSystemLoader("app/templates"))
    template = env.get_template(template)
    return template.render(**kwargs)


def upload_image(asset_id: str, image: Any) -> str:
    try:
        response = upload(
            image,
            asset_folder=asset_id,
            use_asset_folder_as_public_id_prefix=True,
            use_filename=True,
            allowed_formats="pdf,png,jpg,jpeg,mp4",
        )
        return response["secure_url"]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error occurred while uploading image: {e}",
        )


def delete_folder_by_prefix(prefix: str) -> None:
    try:
        delete_resources_by_prefix(prefix)
        delete_folder(prefix)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error occurred while deleting folder: {e}",
        )
