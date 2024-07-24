from typing import Optional
import uuid

from pydantic import BaseModel, EmailStr, ConfigDict

from .enums import UserRoleType


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenPayload(BaseModel):
    email: EmailStr


class UserBase(BaseModel):
    full_name: str
    email: EmailStr
    role: UserRoleType = UserRoleType.USER


class UserCreate(UserBase):
    password: str


class VendorProfileCreate(UserBase):
    phone_number: Optional[str] = None
    proof_of_identity_type: Optional[str] = None
    proof_of_identity_image: Optional[str] = None
    business_registration_certificate_image: Optional[str] = None


class User(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    is_active: bool
