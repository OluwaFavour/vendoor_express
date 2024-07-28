from pydantic import BaseModel, EmailStr, field_validator


class Token(BaseModel):
    access_token: str
    access_token_expires_in_minutes: int
    token_type: str


class TokenPayload(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    new_password: str

    @field_validator("new_password")
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
