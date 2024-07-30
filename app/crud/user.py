import uuid
from typing import Any, Optional

from sqlalchemy import update
from sqlalchemy.future import select
from sqlalchemy.orm import Session

from ..db.models import User as UserModel
from ..core.security import hash_password
from ..schemas.user import UserCreate


def get_user(db: Session, user_id: uuid.UUID) -> UserModel | None:
    return db.execute(select(UserModel).filter_by(id=user_id)).scalar_one_or_none()


def get_user_by_email(db: Session, email: str) -> UserModel | None:
    return db.execute(select(UserModel).filter_by(email=email)).scalar_one_or_none()


def update_user(db: Session, user: UserModel, **kwargs) -> UserModel:
    values: dict[str, Any] = {}
    for key, value in kwargs.items():
        if not hasattr(user, key):
            raise ValueError(f"User model does not have attribute {key}")
        values[key] = value
    db.execute(update(UserModel).filter_by(id=user.id).values(**values))
    db.commit()
    return get_user(db, user.id)


def create_user(db: Session, user: UserCreate) -> UserModel:
    user_data = user.model_dump()
    hashed_password = hash_password(user_data.pop("password"))
    db_user = UserModel(**user_data, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
