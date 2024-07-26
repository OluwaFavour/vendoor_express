from pydantic import BaseModel, EmailStr


class Token(BaseModel):
    access_token: str
    access_token_expires_in_minutes: int
    token_type: str


class TokenPayload(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    new_password: str
