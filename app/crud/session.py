import datetime
import uuid

from sqlalchemy import delete
from sqlalchemy.orm import Session
from sqlalchemy.future import select

from ..db.models import (
    SessionData as SessionModel,
)


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


def get_session(db: Session, session_id: uuid.UUID) -> SessionModel | None:
    return db.execute(
        select(SessionModel).filter_by(id=session_id)
    ).scalar_one_or_none()
