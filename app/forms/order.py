from typing import Annotated, Optional
from uuid import UUID

from fastapi import Form

from ..db.enums import PaymentMethodType


class CheckoutForm:
    def __init__(
        self,
        address_id: Annotated[UUID, Form(title="Address ID")],
        payment_method: Annotated[
            PaymentMethodType,
            Form(
                title="Payment Method",
                description="The payment method to use for the order",
            ),
        ],
        payment_intent_id: Annotated[
            Optional[UUID],
            Form(
                title="Card ID",
                description="The ID of the card used for the order",
            ),
        ] = None,
    ):
        self.address_id = address_id
        self.payment_method = payment_method
        self.payment_intent_id = payment_intent_id

    def dict(self):
        if (
            self.payment_method != PaymentMethodType.PAYMENT_ON_DELIVERY
            and not self.payment_intent_id
        ):
            raise ValueError("Payment intent ID is required for this payment method")
        if self.payment_method == PaymentMethodType.PAYMENT_ON_DELIVERY:
            return {
                "address_id": self.address_id,
                "payment_method": self.payment_method,
            }
        return {
            "address_id": self.address_id,
            "payment_method": self.payment_method,
            "payment_intent_id": self.payment_intent_id,
        }
