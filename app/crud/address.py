from sqlalchemy import delete, update
from sqlalchemy.orm import Session
from sqlalchemy.future import select

from ..db.models import Address, User, DefaultAddress


def get_addresses(db: Session, user_id: int):
    return db.execute(select(Address).filter_by(user_id=user_id)).scalars().all()


def get_address(db: Session, address_id: int):
    return db.execute(select(Address).filter_by(id=address_id)).scalar()


def create_address(db: Session, address: Address):
    db.add(address)
    db.commit()
    db.refresh(address)
    return address


def delete_address(db: Session, address_id: int):
    db.execute(delete(Address).where(Address.id == address_id))
    db.commit()


def create_default_address(db: Session, user_id: int, address_id: int):
    default_address = DefaultAddress(user_id=user_id, address_id=address_id)
    db.add(default_address)
    db.commit()
    db.refresh(default_address)
    return default_address


def update_default_address(db: Session, user: User, address_id: int):
    default_address = user.default_address
    default_address.address_id = address_id
    db.commit()
    db.refresh(default_address)
    return default_address
