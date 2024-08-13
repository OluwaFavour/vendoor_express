from typing import Optional
from uuid import UUID

from sqlalchemy.future import select
from sqlalchemy.orm import Session

from ..db.enums import PaymentMethodType, PaymentStatus
from ..db.models import Order, OrderItem, User
from .cart import get_cart_summary


def create_order_item(
    db: Session, order_id: UUID, product_id: UUID, quantity: int
) -> OrderItem:
    order_item = OrderItem(order_id=order_id, product_id=product_id, quantity=quantity)
    db.add(order_item)
    db.commit()
    db.refresh(order_item)
    return order_item


def create_order(
    db: Session,
    user: User,
    payment_method: PaymentMethodType,
    payment_intent_id: Optional[UUID],
    paystack_transaction_id: Optional[int],
    order_number: str,
    address_id: UUID,
    payment_status: PaymentStatus = PaymentStatus.PENDING,
) -> Order:
    order = Order(
        user=user,
        payment_method=payment_method.value,
        address_id=address_id,
        order_number=order_number,
        paystack_transaction_id=paystack_transaction_id,
        payment_status=payment_status.value,
    )
    db.add(order)
    if payment_method in [PaymentMethodType.CARD, PaymentMethodType.BANK_TRANSFER]:
        pass
    else:
        order.card_id = payment_intent_id
    db.commit()
    db.refresh(order)
    return order


def checkout(
    db: Session,
    user: User,
    payment_method: PaymentMethodType,
    paystack_transaction_id: Optional[int],
    payment_intent_id: Optional[UUID],
    order_number: str,
    address_id: UUID,
    payment_status: PaymentStatus = PaymentStatus.PENDING,
) -> Order:
    order = create_order(
        db,
        user,
        payment_method,
        payment_intent_id,
        paystack_transaction_id,
        order_number,
        address_id,
        payment_status,
    )
    total_amount, _ = get_cart_summary(db, user)
    order.total_amount = total_amount
    for cart_item in user.cart:
        create_order_item(db, order.id, cart_item.product_id, cart_item.quantity)
    user.cart.clear()
    db.commit()
    return order


def get_order_by_id(db: Session, user: User, order_id: UUID) -> Optional[Order]:
    return db.execute(
        select(Order).filter_by(id=order_id, user_id=user.id)
    ).scalar_one_or_none()


def get_orders(user: User) -> list[Order]:
    return user.orders


def update_order_item_status(
    db: Session, order_item_id: UUID, status: str
) -> OrderItem:
    if (
        order_item := db.execute(
            select(OrderItem).filter_by(id=order_item_id)
        ).scalar_one_or_none()
    ) is None:
        raise ValueError(f"Order item {order_item_id} not found")
    order_item.status = status
    db.commit()
    db.refresh(order_item)
    return order_item
