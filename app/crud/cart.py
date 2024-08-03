from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import delete
from sqlalchemy.orm import Session
from sqlalchemy.future import select
from ..db.models import User, CartItem


def add_product_to_cart(
    db: Session, product_id: UUID, user: User, quantity: int = 1
) -> CartItem:
    cart_item = CartItem(product_id=product_id, user_id=user.id, quantity=quantity)
    db.add(cart_item)
    db.commit()
    db.refresh(cart_item)
    return cart_item


def get_cart_item(db: Session, cart_item_id: UUID) -> Optional[CartItem]:
    return db.execute(
        select(CartItem).filter(
            CartItem.id == cart_item_id,
        )
    ).scalar_one_or_none()


def remove_product_from_cart(db: Session, cart_item: CartItem) -> None:
    db.delete(cart_item)
    db.commit()


def update_cart_item_quantity(
    db: Session, cart_item: CartItem, quantity: int
) -> CartItem:
    cart_item.quantity = quantity
    db.commit()
    db.refresh(cart_item)
    return cart_item


def get_cart_items(db: Session, user: User) -> list[CartItem]:
    return (
        db.execute(
            select(CartItem).filter(
                CartItem.user_id == user.id,
            )
        )
        .scalars()
        .all()
    )


def get_cart_item_by_product_id(
    db: Session, user: User, product_id: UUID
) -> Optional[CartItem]:
    return db.execute(
        select(CartItem).filter(
            CartItem.user_id == user.id,
            CartItem.product_id == product_id,
        )
    ).scalar_one_or_none()


def get_cart_summary(db: Session, user: User) -> tuple[Decimal, int]:
    cart_items: list[CartItem] = get_cart_items(db, user)
    total: Decimal = Decimal(0)
    count: int = 0
    for cart_item in cart_items:
        total += cart_item.product.price * cart_item.quantity
        count += 1
    return total, count


def delete_cart(db: Session, user: User) -> None:
    db.execute(delete(CartItem).filter(CartItem.user_id == user.id))
    db.commit()
