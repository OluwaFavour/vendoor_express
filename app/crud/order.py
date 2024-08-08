from datetime import date
from typing import Optional
from uuid import UUID

from sqlalchemy.future import select
from sqlalchemy.orm import Session

from ..db.enums import PaymentMethodType
from ..db.models import Order, OrderItem, User


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
    address_id: UUID,
) -> Order:
    order_count = user.orders.count() + 1
    current_date = date.today()
    order_number = f"{current_date.year}{current_date.month:02d}{current_date.day:02d}-{order_count}"
    order = Order(
        user=user,
        payment_method=payment_method.value,
        address_id=address_id,
        order_number=order_number,
    )
    db.add(order)
    if payment_method == PaymentMethodType.PAYMENT_ON_DELIVERY:
        pass
    elif payment_method == PaymentMethodType.BANK_TRANSFER:
        order.bank_id = payment_intent_id
    else:
        order.card_id = payment_intent_id
    db.commit()
    db.refresh(order)
    return order


def checkout(
    db: Session,
    user: User,
    payment_method: PaymentMethodType,
    payment_intent_id: Optional[UUID],
    address_id: UUID,
) -> Order:
    order = create_order(db, user, payment_method, payment_intent_id, address_id)
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
