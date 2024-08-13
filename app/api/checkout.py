from requests.exceptions import HTTPError
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Form, Request, Query
from sqlalchemy.orm import Session

from ..core.paystack import Paystack
from ..core.utils import (
    generate_reference,
    process_paystack_response,
    process_verification,
    validate_card,
    validate_payment_method,
)
from ..crud import cart as cart_crud, order as order_crud
from ..db.enums import PaymentMethodType
from ..db.models import User as UserModel
from ..dependencies import get_db, get_current_active_user, get_paystack_client
from ..schemas.checkout import Order as OrderSchema, PaystackInitializationResponse

router = APIRouter(tags=["checkout"], prefix="/api/checkout")


@router.post(
    "/",
    summary="Initialize Checkout Transaction",
)
def checkout(
    address_id: Annotated[UUID, Form(title="Address ID")],
    card_id: Annotated[Optional[UUID], Form(title="Card ID")],
    payment_method: Annotated[PaymentMethodType, Form(title="Payment Method")],
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[UserModel, Depends(get_current_active_user)],
    request: Request,
    paystack: Annotated[Paystack, Depends(get_paystack_client)],
    make_default: Annotated[
        Optional[bool], Form(title="Make Default", include_in_schema=False)
    ] = None,
) -> PaystackInitializationResponse | OrderSchema:
    """
    Initialize a checkout transaction.

    Args:
        address_id (UUID): The ID of the address to use for the order.
        card_id (Optional[UUID]): The ID of the card to use for the payment.
        payment_method (PaymentMethodType): The payment method to use.
        user (UserModel): The current user.
        request (Request): The request object.
        paystack (Paystack): The Paystack client.

    Returns:
        dict: The JSON response from the Paystack API.
    """
    try:
        # Generate reference
        reference = generate_reference(user)

        # Validate card
        card = validate_card(db, card_id, user)

        # Validate payment method
        if payment_method == PaymentMethodType.PAYMENT_ON_DELIVERY:
            return order_crud.checkout(
                db=db,
                user=user,
                address_id=address_id,
                payment_method=payment_method,
                payment_intent_id=None,
                paystack_transaction_id=None,
                order_number=reference,
            )

        # Determine channel
        channels = []
        if payment_method == PaymentMethodType.CARD:
            channels.append("card")
        elif payment_method == PaymentMethodType.BANK_TRANSFER:
            channels.append("bank_transfer")

        # Initialize transaction
        amount, _ = cart_crud.get_cart_summary(db, user)
        email = user.email
        callback_url = f"{request.base_url}/api/checkout/verify"
        currency = "NGN"
        metadata = {
            "address_id": str(address_id),
            "make_default": make_default or False,
        }
        if card_id:
            paystack_response = paystack.charge_authorization(
                card.authorization_code, email, amount, reference, channels=channels
            )
        else:
            paystack_response = paystack.initialize_transaction(
                amount, email, reference, callback_url, currency, metadata, channels
            )

        return process_paystack_response(
            db, user, paystack_response, card_id, address_id, reference
        )

    except HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "An error occurred while processing your payment.",
                "error": str(e),
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/verify",
    response_model=OrderSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Verify Checkout Transaction",
)
def verify(
    reference: Annotated[str, Query(title="Reference ID")],
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[UserModel, Depends(get_current_active_user)],
    paystack: Annotated[Paystack, Depends(get_paystack_client)],
):
    """
    Verify a checkout transaction.

    Args:
        reference (str): The reference ID of the transaction.
        db (Session): The database session.
        user (UserModel): The current user.
        paystack (Paystack): The Paystack client.

    Returns:
        OrderSchema: The order object.
    """
    try:
        paystack_response = paystack.verify_transaction(reference)
        if not paystack_response.get("status"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=paystack_response.get("message", "Verification failed."),
            )

        return process_verification(db, user, paystack_response)

    except HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "An error occurred while verifying your payment.",
                "error": str(e),
            },
        )
