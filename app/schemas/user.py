from typing import Optional, Annotated
import uuid

from pydantic import BaseModel, EmailStr, ConfigDict, field_validator, Field

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
        return value

    @field_validator("email")
    def email_validator(cls, value: str):
        return value.lower()


class UserCreate(UserBase):
    password: Annotated[
        str,
        Field(
            ...,
            description="Password of the user, must be at least 8 characters long, contain at least one digit, one uppercase letter, one lowercase letter, one special character and must not contain spaces",
        ),
    ]

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


class User(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    is_active: bool


class Page(BaseModel):
    page: int
    page_size: int
    total_pages: int
    total_users: int
    users: list[User]
