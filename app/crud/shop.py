import uuid
from typing import Any, Union, Optional

from fastapi import UploadFile
from sqlalchemy import update
from sqlalchemy.orm import Session
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from ..core.utils import upload_image
from ..core.debug import logger
from ..crud.user import update_user
from ..db.enums import UserRoleType, ProofOfIdentityType
from ..db.models import User, Shop, ShopMember, Product
from ..forms.shop import VendorProfileCreationForm


def check_shop_name_uniqueness(db: Session, name: str) -> Union[Shop, None]:
    return db.execute(select(Shop).where(Shop.name.ilike(name))).scalar_one_or_none()


def create_shop(db: Session, form_data: VendorProfileCreationForm, user: User) -> Shop:
    form_data: dict[str, Any] = form_data.dict()
    if check_shop_name_uniqueness(db, form_data["name"]) is not None:
        raise IntegrityError(None, None, BaseException("Shop name already exists"))
    user_phone_number: str = form_data.pop("user_phone_number")
    user_role = form_data.pop("user_role")
    proof_of_identity_type: ProofOfIdentityType = form_data.pop(
        "proof_of_identity_type"
    )
    proof_of_identity_image: UploadFile = form_data.pop("proof_of_identity_image")
    business_registration_certificate_image: UploadFile = form_data.pop(
        "business_registration_certificate_image"
    )
    logo: UploadFile = form_data.pop("logo")
    shop = Shop(**form_data, vendor_id=user.id)

    user = update_user(
        db,
        user,
        phone_number=user_phone_number,
        role=user_role if user.role != UserRoleType.ADMIN.value else user.role,
        proof_of_identity_type=proof_of_identity_type,
        is_shop_owner=True,
    )

    # Upload images
    proof_of_identity_image_url = upload_image(
        f"{user.id}/verification/{proof_of_identity_type.name}",
        proof_of_identity_image.file,
    )
    business_registration_certificate_image_url = upload_image(
        f"{user.id}/verification/business_registration_certificate",
        business_registration_certificate_image.file,
    )
    logo_url: str = upload_image(f"{user.id}/shop/logo", logo.file)
    shop.logo = logo_url
    user.proof_of_identity_image = proof_of_identity_image_url
    user.business_registration_certificate_image = (
        business_registration_certificate_image_url
    )
    db.add(shop)
    db.commit()
    db.refresh(shop)
    return shop


def get_shop(db: Session, shop_id: uuid.UUID):
    return db.execute(select(Shop).filter_by(id=shop_id)).scalar_one_or_none()


def update_shop(db: Session, shop: Shop, **kwargs) -> Shop:
    values: dict[str, Any] = {}
    for key, value in kwargs.items():
        if not hasattr(shop, key):
            raise ValueError(f"Shop model does not have attribute {key}")
        if value is not None:
            values[key] = value
    if "name" in values:
        if check_shop_name_uniqueness(db, values["name"]) is not None:
            raise IntegrityError(None, None, BaseException("Shop name already exists"))
    if "logo" in values:
        values["logo"] = upload_image(str(shop.id), values["logo"].file)
    if "cover_photo" in values:
        values["cover_photo"] = upload_image(
            f"{shop.vendor_id}/shop/cover_photo", values["cover_photo"].file
        )
    db.execute(update(Shop).filter_by(id=shop.id).values(**values))
    db.commit()
    return shop


def add_product_to_shop(db: Session, shop: Shop, product: Product) -> Product:
    """Add a product to a shop."""
    shop.products.append(product)
    db.commit()
    db.refresh(product)
    return product


def get_product_in_shop(
    db: Session, shop: Shop, product_id: uuid.UUID
) -> Optional[Product]:
    """Get a product by ID within a specific shop."""
    return db.execute(
        select(Product).filter(Product.shop_id == shop.id, Product.id == product_id)
    ).scalar_one_or_none()


def list_products_in_shop(db: Session, shop: Shop) -> list[Product]:
    """List all products within a specific shop."""
    return (
        db.execute(select(Product).filter(Product.shop_id == shop.id)).scalars().all()
    )


def get_shop_staffs(db: Session, shop: Shop) -> list[ShopMember]:
    return shop.members


def get_shop_staff(
    db: Session, shop: Shop, staff_id: uuid.UUID
) -> Optional[ShopMember]:
    staff = db.execute(select(ShopMember).filter_by(id=staff_id)).scalar_one_or_none()
    if staff is None:
        return None
    if staff.shop_id != shop.id:
        raise IntegrityError(None, None, BaseException("Staff does not belong to shop"))
    return staff


def add_staff_to_shop(db: Session, shop: Shop, **kwargs) -> ShopMember:
    required_fields = ["full_name", "role"]
    for field in required_fields:
        if field not in kwargs:
            raise ValueError(f"Field {field} is required")
    for field in kwargs:
        if not hasattr(ShopMember, field):
            raise ValueError(f"ShopMember model does not have attribute {field}")
    if "profile_image" in kwargs and kwargs["profile_image"] is not None:
        profile_image: UploadFile = kwargs.pop("profile_image")
    staff = ShopMember(**kwargs)
    profile_image = upload_image(
        f"{shop.vendor_id}/shop/staff/{staff.id}", profile_image.file
    )
    staff.profile_image = profile_image
    shop.members.append(staff)
    db.commit()
    db.refresh(staff)
    return staff


def update_shop_staff(db: Session, staff: ShopMember, **kwargs) -> ShopMember:
    values: dict[str, Any] = {}
    for key, value in kwargs.items():
        if not hasattr(staff, key):
            raise ValueError(f"ShopMember model does not have attribute {key}")
        if value is not None:
            values[key] = value
    if "profile_image" in values and values["profile_image"] is not None:
        values["profile_image"] = upload_image(
            f"{staff.shop.vendor_id}/shop/staff/{staff.id}",
            values["profile_image"].file,
        )
    db.execute(update(ShopMember).filter_by(id=staff.id).values(**values))
    db.commit()
    return staff
