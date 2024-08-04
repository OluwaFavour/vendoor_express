import datetime
import jwt
import uuid
from smtplib import SMTP
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Path, Form, Request
from fastapi.responses import JSONResponse
from pydantic import EmailStr
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from twilio.rest import Client

from ..core.config import settings
from ..core.debug import logger
from ..core.security import hash_password, verify_password
from ..core.utils import generate_otp, get_html_from_template, send_email, send_sms
from ..db.models import User as UserModel
from ..schemas.shop import Shop, StaffMember
from ..crud.shop import (
    create_shop,
    update_shop,
    add_staff_to_shop,
    update_shop_staff,
    get_shop_staff,
    get_shop_staffs,
)
from ..dependencies import (
    get_current_active_user,
    get_db,
    get_smtp,
    get_current_active_verified_vendor,
    get_current_active_vendor,
    get_twilio_client,
)
from ..forms.shop import VendorProfileCreationForm, ShopUpdateForm, StaffMemberForm


router = APIRouter(prefix="/api/shop", tags=["shop"])


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=Shop,
    summary="Create a vendor profile",
)
def create_vendor_profile(
    db: Annotated[Session, Depends(get_db)],
    vendor_profile: Annotated[VendorProfileCreationForm, Depends()],
    user: Annotated[UserModel, Depends(get_current_active_user)],
):
    try:
        shop = create_shop(db, vendor_profile, user)
        return shop
    except IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e.orig),
        )


@router.post(
    "/send-verification-sms",
    status_code=status.HTTP_200_OK,
    summary="Send verification SMS OTP",
)
def send_verification_sms(
    phone_number: Annotated[
        str,
        Form(
            title="Phone Number", description="Phone number", example="+2348123456789"
        ),
    ],
    twilio: Annotated[Client, Depends(get_twilio_client)],
):
    otp = generate_otp()

    # Encode the OTP into a JWT token and store in session cookie
    expires_in_minutes = 5
    expire = datetime.datetime.now(datetime.UTC) + datetime.timedelta(
        minutes=expires_in_minutes
    )
    salt = hash_password(otp)
    data = {
        "sub": f"{salt}",
        "exp": expire,
    }
    to_encode = data.copy()
    token = jwt.encode(to_encode, settings.secret_key, settings.algorithm)

    sms_body = f"Your OTP is: {otp}"
    send_sms(twilio, phone_number, sms_body)
    response = JSONResponse(content={"message": "OTP sent as SMS"})
    response.set_cookie(
        key="sms_otp",
        value=token,
        httponly=True,
        samesite=settings.same_site,
        max_age=expires_in_minutes * 60,
        secure=settings.https_only,
    )
    return response


@router.post(
    "/verify-verification-sms",
    status_code=status.HTTP_200_OK,
    summary="Verify verification sms OTP",
)
def verify_verification_sms(
    otp: Annotated[str, Form(title="OTP", description="OTP")], request: Request
):
    sms_otp = request.cookies.get("sms_otp")
    if sms_otp is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP not found",
        )
    try:
        payload = jwt.decode(
            sms_otp, settings.secret_key, algorithms=[settings.algorithm]
        )
        salt = payload["sub"]
        if verify_password(otp, salt):
            response = JSONResponse(content={"message": "OTP verified"})
            response.delete_cookie("sms_otp")
            return response
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP does not match",
            )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP has expired",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OTP",
        )


@router.post(
    "/send-verification-email-otp",
    status_code=status.HTTP_200_OK,
    summary="Send verification email OTP",
)
def send_verification_email_otp(
    email: Annotated[EmailStr, Form(title="Email", description="Email")],
    smtp: Annotated[SMTP, Depends(get_smtp)],
):
    otp = generate_otp()

    # Encode the OTP into a JWT token and store in session cookie
    expires_in_minutes = 5
    expire = datetime.datetime.now(datetime.UTC) + datetime.timedelta(
        minutes=expires_in_minutes
    )
    salt = hash_password(otp)
    data = {
        "sub": f"{salt}",
        "exp": expire,
    }
    to_encode = data.copy()
    token = jwt.encode(to_encode, settings.secret_key, settings.algorithm)

    # Send email
    plain_text = f"Your OTP is: {otp}"
    html_text = get_html_from_template("email_otp_verification.html", otp=otp)
    send_email(
        smtp=smtp,
        subject="Vendoor Express - Email Verification",
        recipient=email,
        plain_text=plain_text,
        html_text=html_text,
        sender=settings.from_email,
    )
    response = JSONResponse(content={"message": "OTP sent to email"})
    response.set_cookie(
        key="email_otp",
        value=token,
        httponly=True,
        samesite=settings.same_site,
        max_age=expires_in_minutes * 60,
        secure=settings.https_only,
    )
    return response


@router.post(
    "/verify-email-otp",
    status_code=status.HTTP_200_OK,
    summary="Verify email OTP",
)
def verify_email_otp(
    otp: Annotated[str, Form(title="OTP", description="OTP")], request: Request
):
    email_otp = request.cookies.get("email_otp")
    if email_otp is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP not found",
        )
    try:
        payload = jwt.decode(
            email_otp, settings.secret_key, algorithms=[settings.algorithm]
        )
        salt = payload["sub"]
        if verify_password(otp, salt):
            response = JSONResponse(content={"message": "OTP verified"})
            response.delete_cookie("email_otp")
            return response
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP does not match",
            )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP has expired",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OTP",
        )


@router.get(
    "/me",
    response_model=Shop,
    status_code=status.HTTP_200_OK,
    summary="Get vendor profile",
)
def read_shop_me(
    current_vendor: Annotated[UserModel, Depends(get_current_active_vendor)]
) -> Shop:
    return current_vendor.shop


@router.patch(
    "/me",
    response_model=Shop,
    status_code=status.HTTP_200_OK,
    summary="Update vendor profile",
)
def update_vendor_profile(
    db: Annotated[Session, Depends(get_db)],
    form_data: Annotated[ShopUpdateForm, Depends()],
    current_vendor: Annotated[UserModel, Depends(get_current_active_verified_vendor)],
):
    try:
        shop = update_shop(db, current_vendor.shop, **form_data.dict())
        return shop
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e.orig),
        )


@router.post("/me/staffs/", status_code=status.HTTP_201_CREATED, summary="Add a staff")
def add_staff(
    db: Annotated[Session, Depends(get_db)],
    form_data: Annotated[StaffMemberForm, Depends()],
    current_vendor: Annotated[UserModel, Depends(get_current_active_verified_vendor)],
) -> StaffMember:
    try:
        shop = current_vendor.shop
        staff = add_staff_to_shop(db, shop, **form_data.dict())
        return staff
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.patch(
    "/me/staffs/{staff_id}",
    response_model=StaffMember,
    status_code=status.HTTP_200_OK,
    summary="Update staff",
)
def update_staff(
    db: Annotated[Session, Depends(get_db)],
    form_data: Annotated[StaffMemberForm, Depends()],
    staff_id: Annotated[uuid.UUID, Path(title="Staff ID", description="Staff ID")],
    current_vendor: Annotated[UserModel, Depends(get_current_active_verified_vendor)],
):
    try:
        staff = get_shop_staff(db, current_vendor.shop, staff_id)
        if staff is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Staff not found",
            )
        update_shop_staff(db, staff, **form_data.dict())
        return staff
    except IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e.orig),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except HTTPException as e:
        raise e


@router.get(
    "/me/staffs/",
    response_model=list[StaffMember],
    status_code=status.HTTP_200_OK,
    summary="Get all staffs",
)
def get_staffs(
    db: Annotated[Session, Depends(get_db)],
    current_vendor: Annotated[UserModel, Depends(get_current_active_verified_vendor)],
):
    staffs = get_shop_staffs(db, current_vendor.shop)
    return staffs
