import uuid
from typing import Any

from sqlalchemy import update
from sqlalchemy.future import select
from sqlalchemy.orm import Session

from ..db.models import User as UserModel
from ..db.enums import UserRoleType
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
    return user


def create_user(db: Session, user: UserCreate) -> UserModel:
    user_data = user.model_dump()
    hashed_password = hash_password(user_data.pop("password"))
    db_user = UserModel(**user_data, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_all_users(db: Session, **filters) -> list[UserModel]:
    possible_filters = ["role", "is_active", "is_shop_owner", "search_query"]
    invalid_filters = set(filters.keys()) - possible_filters
    if invalid_filters:
        raise ValueError(f"Invalid filters: {invalid_filters}")

    query = select(UserModel)

    for filter_key, value in filters.items():
        if filter_key == "search_query":
            query = query.filter(
                UserModel.full_name.ilike(f"%{value}%")
                | UserModel.email.ilike(f"%{value}%")
                | UserModel.phone_number.ilike(f"%{value}%")
            )
        elif filter_key == "role":
            if value not in UserRoleType.__members__:
                raise ValueError(f"Invalid role: {value}")
            query = query.filter(UserModel.role == value)
        elif filter_key == "is_active":
            query = query.filter(UserModel.is_active == value)
        elif filter_key == "is_shop_owner":
            query = query.filter(UserModel.is_shop_owner == value)

    return db.execute(query).scalars().all()
