from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class CartBase(BaseModel):
    user_id: UUID
    product_id: UUID
    quantity: int


class Cart(CartBase):
    model_config: ConfigDict = ConfigDict(from_attributes=True)
    id: UUID


class CartSummary(BaseModel):
    model_config: ConfigDict = ConfigDict(from_attributes=True)
    user_id: UUID
    total_items: int
    total_cost: Decimal = Field(title="Total Cost", decimal_places=2)
