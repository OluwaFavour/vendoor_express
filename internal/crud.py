import datetime
import uuid
from typing import Any

from sqlalchemy import delete, update
from sqlalchemy.exc import NoResultFound
from sqlalchemy.future import select
from sqlalchemy.orm import Session

from .models import User as UserModel, Token as TokenModel
from .schemas import UserCreate


def store_token(
    user: UserModel, db: Session, token_jti: str, expires_at: datetime.datetime
) -> TokenModel:
    token = TokenModel(
        user_id=user.id,
        jti=token_jti,
        expires_at=expires_at,
    )
    db.add(token)
    db.commit()
    db.refresh(token)
    return token


def delete_token(db: Session, token_jti: str) -> None:
    db.execute(delete(TokenModel).filter_by(jti=token_jti))
    db.commit()


def delete_user_tokens(db: Session, user: UserModel) -> None:
    user.tokens.clear()
    db.commit()


def get_token(db: Session, token_jti: str) -> TokenModel | None:
    try:
        return db.execute(select(TokenModel).filter_by(jti=token_jti)).scalar_one()
    except NoResultFound:
        return None


def get_user(db: Session, user_id: uuid.UUID) -> UserModel | None:
    try:
        return db.execute(select(UserModel).filter_by(id=user_id)).scalar_one()
    except NoResultFound:
        return None


def get_user_by_email(db: Session, email: str) -> UserModel | None:
    try:
        return db.execute(select(UserModel).filter_by(email=email)).scalar_one()
    except NoResultFound:
        return None


def update_user(db: Session, user: UserModel, **kwargs) -> UserModel:
    values: dict[str, Any] = {}
    for key, value in kwargs.items():
        if not hasattr(user, key):
            raise ValueError(f"User model does not have attribute {key}")
        values[key] = value
    user = db.execute(
        update(UserModel).where(UserModel.id == user.id).values(**values)
    ).scalar_one()
    return user


def get_users(db: Session, skip: int = 0, limit: int = 100) -> list[UserModel]:
    return db.execute(select(UserModel).offset(skip).limit(limit)).scalars().all()


def create_user(db: Session, user: UserCreate) -> UserModel:
    from .utils import hash_password

    user_data = user.model_dump()
    hashed_password = hash_password(user_data.pop("password"))
    db_user = UserModel(**user_data, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
