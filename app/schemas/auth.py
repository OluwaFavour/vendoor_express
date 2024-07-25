from pydantic import BaseModel, EmailStr


class Token(BaseModel):
    access_token: str
    access_token_expires_in_minutes: int
    refresh_token: str
    refresh_token_expires_in_days: int
    token_type: str


class RefreshTokenOut(BaseModel):
    access_token: str
    access_token_expires_in_minutes: int
    refresh_token: str
    refresh_token_expires_in_days: int
    token_type: str


class TokenPayload(BaseModel):
    email: EmailStr
