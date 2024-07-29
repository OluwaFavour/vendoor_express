import datetime
import uuid
from typing import Optional, Any

from sqlalchemy import delete, update
from sqlalchemy.orm import Session
from sqlalchemy.future import select

from ..db.enums import TokenType
from ..db.models import (
    User as UserModel,
    Token as TokenModel,
    SessionData as SessionModel,
)


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


def store_session(
    db: Session,
    session_id: uuid.UUID,
    data: str,
    user_agent: str,
    ip_address: str,
    expires_at: datetime.datetime,
) -> SessionModel:
    session = SessionModel(
        id=session_id,
        user_id=data,
        expires_at=expires_at,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_session_by_user_id(db: Session, data: str) -> SessionModel | None:
    return db.execute(select(SessionModel).filter_by(user_id=data)).scalar_one_or_none()


def delete_session_by_user_id(db: Session, data: str) -> None:
    db.execute(delete(SessionModel).filter_by(user_id=data))
    db.commit()


def delete_session(db: Session, session_id: uuid.UUID) -> None:
    db.execute(delete(SessionModel).filter_by(id=session_id))
    db.commit()


def delete_sessions_by_user_id(db: Session, data: str) -> None:
    db.execute(delete(SessionModel).filter_by(user_id=data))
    db.commit()


def get_session(db: Session, session_id: uuid.UUID) -> SessionModel | None:
    return db.execute(
        select(SessionModel).filter_by(id=session_id)
    ).scalar_one_or_none()


def invalidate_token(db: Session, token_type: str, token_jti: str) -> None:
    db.execute(
        update(TokenModel)
        .filter_by(jti=token_jti, token_type=token_type)
        .values(is_active=False)
    )
    db.commit()


def invalidate_all_user_access_tokens(
    db: Session, user: UserModel, token_type: Optional[str] = TokenType.ACCESS.value
) -> None:
    db.execute(
        update(TokenModel)
        .filter_by(user_id=user.id, is_active=True, token_type=token_type)
        .values(is_active=False)
    )
    db.commit()


def get_token(db: Session, token_jti: str) -> TokenModel | None:
    return db.execute(select(TokenModel).filter_by(jti=token_jti)).scalar_one_or_none()


def delete_token(db: Session, token_jti: str) -> None:
    db.execute(delete(TokenModel).filter_by(jti=token_jti))
    db.commit()


def delete_tokens_by_type(db: Session, user_id: uuid.UUID, token_type: str) -> None:
    db.execute(delete(TokenModel).filter_by(user_id=user_id, token_type=token_type))
    db.commit()


def delete_user_tokens(db: Session, user: UserModel) -> None:
    user.tokens.clear()
    db.commit()
