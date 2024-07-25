import datetime
import uuid

from sqlalchemy import delete, update
from sqlalchemy.orm import Session
from sqlalchemy.future import select

from ..db.enums import TokenType
from ..db.models import User as UserModel, Token as TokenModel


def store_token(
    user_id: uuid.UUID,
    db: Session,
    token_jti: str,
    token_type: str,
    expires_at: datetime.datetime,
    is_active: bool = True,
) -> TokenModel:
    token = TokenModel(
        user_id=user_id,
        jti=token_jti,
        expires_at=expires_at,
        token_type=token_type,
        is_active=is_active,
    )
    db.add(token)
    db.commit()
    db.refresh(token)
    return token


def invalidate_token(db: Session, token_type: str, token_jti: str) -> None:
    return db.execute(
        update(TokenModel)
        .filter_by(jti=token_jti, token_type=token_type)
        .values(is_active=False)
    )


def invalidate_all_user_access_tokens(db: Session, user: UserModel) -> None:
    return db.execute(
        update(TokenModel)
        .filter_by(user_id=user.id, is_active=True, token_type=TokenType.ACCESS.value)
        .values(is_active=False)
    )


def get_token(db: Session, token_jti: str) -> TokenModel | None:
    return db.execute(select(TokenModel).filter_by(jti=token_jti)).scalar_one_or_none()


def delete_token(db: Session, token_jti: str) -> None:
    db.execute(delete(TokenModel).filter_by(jti=token_jti))
    db.commit()


def delete_user_tokens(db: Session, user: UserModel) -> None:
    user.tokens.clear()
    db.commit()
