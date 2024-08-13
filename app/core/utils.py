import uuid
import datetime
from jinja2 import FileSystemLoader, Environment
import jwt
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import secrets
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
from fastapi import HTTPException, status, Depends, Request
from sqlalchemy.orm import Session
from twilio.rest import Client

from .config import settings
from .security import verify_password, hash_password
from ..crud import (
    session as session_crud,
    user as user_crud,
    card as card_crud,
    order as order_crud,
)
from ..db.enums import PaymentMethodType
from ..db.models import User, Card
from ..dependencies import get_db
from ..forms.auth import LoginForm
from ..schemas.user import UserCreate
from ..schemas.checkout import Order as OrderSchema, PaystackInitializationResponse


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
    session = session_crud.store_session(
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
    session_crud.delete_session_by_user_id(db, user_id)


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


def send_verification_email(user_scheme: UserCreate, smtp: SMTP, request: Request):
    salt = hash_password(user_scheme.password)
    expire = datetime.datetime.now(datetime.UTC) + datetime.timedelta(
        minutes=settings.reset_token_expire_minutes
    )
    data = {
        "sub": f"{user_scheme.email}:{salt}:user:{user_scheme.full_name}",
        "exp": expire,
    }
    to_encode = data.copy()
    token = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)

    # Send email
    verification_link = f"{request.base_url}api/users/verify-email?token={token}"
    plain_text = f"Click the link to verify your email: {verification_link}"
    html_text = get_html_from_template(
        "email_verification.html",
        user_name=user_scheme.full_name,
        verification_link=verification_link,
        verification_link_expiry=settings.reset_token_expire_minutes,
    )
    send_email(
        smtp=smtp,
        subject="Vendoor Express - Email Verification",
        recipient=user_scheme.email,
        plain_text=plain_text,
        html_text=html_text,
        sender=settings.from_email,
    )
    return {"message": "Email verification link sent"}


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


def generate_otp() -> str:
    return "".join(
        secrets.choice("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ") for _ in range(6)
    )


def send_sms(
    twilio_client: Client,
    to: str,
    body: str,
) -> None:
    try:
        twilio_client.messages.create(
            to=to,
            from_=settings.twilio_phone_number,
            body=body,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error occurred while sending SMS: {e}",
        )


def validate_card(
    db: Session, card_id: Optional[uuid.UUID], user: User
) -> Optional[Card]:
    if card_id:
        card = card_crud.get_card_by_id(db, card_id)
        if not card:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Card not found."
            )
        if card.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to use this card.",
            )
        return card
    return None


def validate_payment_method(payment_method: PaymentMethodType):
    if payment_method in [
        PaymentMethodType.PAYMENT_ON_DELIVERY,
        PaymentMethodType.BANK_TRANSFER,
    ]:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=f"{payment_method.value} is not supported yet.",
        )


def generate_reference(user: User) -> str:
    order_count = user.orders.count() + 1
    current_date = datetime.date.today()
    return f"{current_date.year}{current_date.month:02d}{current_date.day:02d}-{order_count}"


def process_paystack_response(
    db: Session,
    user: User,
    paystack_response: dict[str, Any],
    card_id: Optional[uuid.UUID],
    address_id: uuid.UUID,
    reference: str,
) -> PaystackInitializationResponse | OrderSchema:
    if paystack_response.get("status"):
        data: dict[str, Any] = paystack_response.get("data", {})
        if card_id:
            if data.get("status") == "success":
                order = order_crud.checkout(
                    db,
                    user,
                    PaymentMethodType.CARD,
                    data.get("id"),
                    card_id,
                    reference,
                    address_id,
                )
                return order
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=data.get(
                        "gateway_response",
                        "An error occurred while processing your payment.",
                    ),
                )
        else:
            if data.get("status") == "success":
                response = PaystackInitializationResponse(
                    message=paystack_response.get("message"),
                    authorization_url=data.get("authorization_url"),
                )
                return response
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=data.get(
                        "gateway_response",
                        "An error occurred while processing your payment.",
                    ),
                )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=paystack_response.get(
                "message", "An error occurred while processing your payment."
            ),
        )


def process_verification(
    db: Session, user: User, paystack_response: dict[str, Any]
) -> OrderSchema:
    data: dict[str, Any] = paystack_response.get("data")
    transaction_id = data.get("id")
    order_number = data.get("reference")
    address_id = uuid.UUID(data.get("metadata", {}).get("address_id"))
    email: str = data.get("customer", {}).get("email")
    authorization: dict[str, Any] = data.get("authorization", {})
    signature: str = authorization.get("signature")
    channel: str = authorization.get("channel")

    if channel == "card":
        card = Card(
            signature=signature,
            bin=authorization.get("bin"),
            last_four=authorization.get("last4"),
            exp_month=authorization.get("exp_month"),
            exp_year=authorization.get("exp_year"),
            country_code=authorization.get("country_code"),
            brand=authorization.get("brand"),
            authorization_code=authorization.get("authorization_code"),
            authorization_email=email,
            bank=authorization.get("bank"),
        )
        card = card_crud.create_card(db, card)

    order = order_crud.checkout(
        db,
        user,
        PaymentMethodType.CARD,
        transaction_id,
        card.id if channel == "card" else None,
        order_number,
        address_id,
    )
    return order
