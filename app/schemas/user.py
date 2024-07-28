from typing import Optional
import uuid

from pydantic import BaseModel, EmailStr, ConfigDict, field_validator

from ..db.enums import UserRoleType


class UserBase(BaseModel):
    full_name: str
    email: EmailStr
    role: UserRoleType = UserRoleType.USER

    @field_validator("full_name")
    def full_name_validator(cls, value: str):
        names = value.strip().split()
        if len(names) < 2:
            raise ValueError("Full name must contain at least two words")
        for name in names:
            if len(name) < 2:
                raise ValueError("Each name must contain at least two characters")
            if not name.isalpha():
                raise ValueError("Each name must contain only alphabetic characters")


class UserCreate(UserBase):
    password: str

    @field_validator("password")
    def password_validator(cls, value: str):
        if not any(char.isdigit() for char in value):
            raise ValueError("Password must contain at least one digit")
        if not any(char.isupper() for char in value):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(char.islower() for char in value):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(char in "!@#$%^&*()-_+=" for char in value):
            raise ValueError("Password must contain at least one special character")
        if " " in value:
            raise ValueError("Password must not contain spaces")
        return value


class VendorProfileCreate(UserBase):
    phone_number: Optional[str] = None
    proof_of_identity_type: Optional[str] = None
    proof_of_identity_image: Optional[str] = None
    business_registration_certificate_image: Optional[str] = None


class User(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    is_active: bool
