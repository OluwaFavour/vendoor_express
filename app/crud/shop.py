from typing import Any, Union

from fastapi import UploadFile
from sqlalchemy.orm import Session

from ..core.utils import upload_image
from ..crud.user import update_user
from ..db.enums import UserRoleType, ProofOfIdentityType
from ..db.models import User, Shop
from ..forms.shop import VendorProfileCreationForm


def create_shop(db: Session, form_data: VendorProfileCreationForm, user: User) -> Shop:
    form_data: dict[str, Any] = form_data.dict()
    user_phone_number: str = form_data.pop("user_phone_number")
    user_role = form_data.pop("user_role")
    proof_of_identity_type: ProofOfIdentityType = form_data.pop(
        "proof_of_identity_type"
    )

    # Upload Image to cloudinary
    proof_of_identity_image: UploadFile = form_data.pop("proof_of_identity_image")
    proof_of_identity_image_url = upload_image(str(user.id), proof_of_identity_image)

    # Upload Image to cloudinary
    business_registration_certificate_image: UploadFile = form_data.pop(
        "business_registration_certificate_image"
    )
    business_registration_certificate_image_url = upload_image(
        str(user.id), business_registration_certificate_image
    )
    user = update_user(
        db,
        user,
        phone_number=user_phone_number,
        role=user_role,
        proof_of_identity_type=proof_of_identity_type,
        proof_of_identity_image=proof_of_identity_image_url,
        business_registration_certificate_image=business_registration_certificate_image_url,
    )

    # Upload Image to cloudinary
    logo: UploadFile = form_data.pop("logo")
    logo_url = upload_image(str(user.id), logo)
    form_data["logo"] = logo_url

    shop = Shop(**form_data, vendor_id=user.id)
    db.add(shop)
    db.commit()
    db.refresh(shop)
    return shop
