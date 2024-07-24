from typing import Optional
import uuid

from pydantic import BaseModel, EmailStr

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
    id: uuid.UUID
    is_active: bool

    class Config:
        from_attributes = True
