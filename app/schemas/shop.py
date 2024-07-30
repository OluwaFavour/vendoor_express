from pydantic import BaseModel, ConfigDict, EmailStr, HttpUrl
from typing import Optional
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
