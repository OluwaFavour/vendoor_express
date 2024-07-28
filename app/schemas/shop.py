from pydantic import BaseModel, ConfigDict
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
    email: str
    phone_number: str
    wanted_help: Optional[WantedHelpType]
    logo: str
    is_verified: bool
    vendor: User
