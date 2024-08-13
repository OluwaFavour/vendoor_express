from typing import Optional
from uuid import UUID

from sqlalchemy import update
from sqlalchemy.orm import Session
from sqlalchemy.future import select

from ..db.models import Card


def create_card(db: Session, card: Card) -> Card:
    db.add(card)
    db.commit()
    db.refresh(card)
    return card


def get_card_by_id(db: Session, card_id: UUID) -> Optional[Card]:
    return db.execute(select(Card).filter(Card.id == card_id)).scalar_one_or_none()


def remove_default_card(db: Session, user_id: UUID):
    db.execute(update(Card).where(Card.user_id == user_id).values(is_default=False))
    db.commit()
