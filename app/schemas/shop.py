from pydantic import BaseModel, ConfigDict, EmailStr, HttpUrl
from typing import Optional
from datetime import datetime
import uuid

from .user import User
from ..db.enums import WantedHelpType


class Shop(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    description: str
    type: str
    category: str
    email: EmailStr
    phone_number: str
    wanted_help: Optional[WantedHelpType]
    logo: HttpUrl
    status: str
    vendor: User
    created_at: datetime


class ShopPage(BaseModel):
    page: int
    page_size: int
    total_pages: int
    total_users: int
    shops: list[Shop]


class StaffMember(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    full_name: str
    role: str
    profile_image: Optional[HttpUrl]
    shop: Shop
