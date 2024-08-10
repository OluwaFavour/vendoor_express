from typing import Optional
from uuid import UUID

from sqlalchemy import delete, update
from sqlalchemy.orm import Session
from sqlalchemy.future import select

from ..db.models import Address, User


def get_addresses(db: Session, user_id: UUID) -> list[Address]:
    return db.execute(select(Address).filter_by(user_id=user_id)).scalars().all()


def get_address(db: Session, address_id: UUID) -> Optional[Address]:
    return db.execute(select(Address).filter_by(id=address_id)).scalar_one_or_none()


def create_address(db: Session, address: Address) -> Address:
    db.add(address)
    db.commit()
    db.refresh(address)
    return address


def delete_address(db: Session, address_id: UUID):
    db.execute(delete(Address).where(Address.id == address_id))
    db.commit()


def get_default_address(db: Session, user_id: UUID) -> Optional[Address]:
    return db.execute(
        select(Address).filter_by(user_id=user_id, is_default=True)
    ).scalar_one_or_none()


def remove_default_address(db: Session, user_id: UUID):
    db.execute(
        update(Address).where(Address.user_id == user_id).values(is_default=False)
    )
    db.commit()


def update_default_address(
    db: Session, user_id: UUID, address_id: UUID
) -> Optional[Address]:
    # Remove old default address
    remove_default_address(db, user_id)
    address = get_address(db, address_id)
    if address is None:
        return None
    address.is_default = True
    return address
