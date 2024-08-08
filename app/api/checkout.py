from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..crud import order as order_crud
from ..db.enums import PaymentMethodType
from ..dependencies import get_db, get_current_active_user
from ..forms.order import CheckoutForm
from ..schemas.checkout import Order as OrderSchema

router = APIRouter(tags=["checkout"], prefix="/api/checkout")


@router.post(
    "/",
    response_model=OrderSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Checkout",
)
def checkout(
    checkout_form: Annotated[CheckoutForm, Depends()],
    db: Session = Depends(get_db),
    user=Depends(get_current_active_user),
):
    """
    Checkout the user's cart.

    Args:
        checkout_form (CheckoutForm): The form containing the checkout data.
        db (Session): The database session.
        user (UserModel): The current user.

    Returns:
        OrderSchema: The created order.

    Raises:
        HTTPException: If there is a value error while processing the checkout form.
    """
    try:
        checkout_data = checkout_form.dict()
        address_id: UUID = checkout_data.pop("address_id")
        payment_method: PaymentMethodType = checkout_data.pop("payment_method")
        payment_intent_id: Optional[UUID] = checkout_data.pop("payment_intent_id", None)
        order = order_crud.checkout(
            db, user, payment_method, payment_intent_id, address_id
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return order
