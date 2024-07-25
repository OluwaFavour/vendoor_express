import datetime

from sqlalchemy import delete
from sqlalchemy.orm import Session

from ..db.models import User as UserModel, Token as TokenModel


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
