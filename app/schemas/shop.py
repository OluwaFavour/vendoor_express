from pydantic import BaseModel
from typing import Optional

from .user import UserBase
from ..db.enums import UserRoleType


class Shop(UserBase):
    full_name: Optional[None] = None
    email: Optional[None] = None
    role: UserRoleType = UserRoleType.VENDOR
    phone_number: Optional[str] = None
    proof_of_identity_type: Optional[str] = None
    proof_of_identity_image: Optional[str] = None
    business_registration_certificate_image: Optional[str] = None
