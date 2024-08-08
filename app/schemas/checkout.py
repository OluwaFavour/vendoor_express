from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from ..db.enums import PaymentMethodType, OrderStatusType
from ..db.models import Order, User, OrderItem


class OrderItemBase(BaseModel):
    product_id: UUID
    quantity: int
    status: str = OrderStatusType.PENDING.value


class OrderItem(OrderItemBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    order_id: UUID


class OrderBase(BaseModel):
    payment_method: str = Field(
        examples=[
            PaymentMethodType.CARD.value,
            PaymentMethodType.BANK_TRANSFER.value,
            PaymentMethodType.PAYMENT_ON_DELIVERY.value,
        ]
    )
    address_id: UUID
    bank_id: Optional[UUID]
    card_id: Optional[UUID]


class Order(OrderBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: UUID
    order_number: str
    status: str = OrderStatusType.PENDING.value
