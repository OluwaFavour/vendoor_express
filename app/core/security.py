import datetime
import jwt
from typing import Optional, Any
import uuid

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..crud import user as user_crud
from ..crud import token as token_crud
from .config import password_context, settings
from .debug import logger
from ..db.enums import TokenType


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify the password
    ### Arguments
    plain_password (str): The plain text password
    hashed_password (str): The hashed password
    """
    return password_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    """
    Hash the password
    ### Arguments
    password (str): The plain text password
    """
    return password_context.hash(password)


def create_token(
    data: dict, db: Session, token_type: str, expires_delta: Optional[datetime.timedelta]
) -> str:
    to_encode = data.copy()
    expire = datetime.datetime.now(datetime.UTC) + expires_delta
    to_encode.update({"exp": expire})
    to_encode.update({"jti": str(uuid.uuid4())})
    encoded_jwt = jwt.encode(
        to_encode, settings.secret_key, algorithm=settings.algorithm
    )
    # Store the token in the database
    token_crud.store_token(
        db=db,
        token_jti=to_encode["jti"],
        expires_at=expire,
        user_id=uuid.UUID(data["sub"]),
        token_type=token_type
    )

    return encoded_jwt


def refresh_access_token(refresh_token: str, db: Session) -> tuple[str, str]:
    """
    Refresh the access token
    ### Arguments
    refresh_token (str): The refresh token
    db (Session): The database session
    """
    try:
        payload: dict[str, Any] = jwt.decode(
            jwt=refresh_token,
            key=settings.secret_key,
            algorithms=[settings.algorithm],
        )
        jti = payload.get("jti")
        if jti is None:
            raise jwt.PyJWTError
        user_id = payload.get("sub")
        user_id = uuid.UUID(user_id)
        if user_id is None:
            raise jwt.PyJWTError
    except jwt.PyJWTError:
        raise jwt.PyJWTError
    user = user_crud.get_user(db=db, user_id=user_id)
    if user is None:
        raise jwt.PyJWTError

    # Check the token in the database
    db_token = token_crud.get_token(db, jti)
    if db_token is None or db_token.is_active is False:
        raise jwt.PyJWTError
    if db_token.expires_at.replace(tzinfo=datetime.UTC) < datetime.datetime.now(
        datetime.UTC
    ):
        try:
            token_crud.invalidate_token(
                db=db, token_jti=jti, token_type=TokenType.REFRESH.value
            )
        except SQLAlchemyError as e:
            logger.error(f"Could not invalidate token: {e}")
            raise SQLAlchemyError("Could not delete token", "error")
        raise jwt.PyJWTError

    # Get the user from the database
    user = user_crud.get_user(db, db_token.user_id)
    if user is None:
        raise jwt.PyJWTError

    # Invalidate all old access tokens
    token_crud.invalidate_all_user_access_tokens(db, user)
    # Create a new access token
    access_token_expires = datetime.timedelta(
        minutes=settings.access_token_expire_minutes
    )
    access_token = create_token(
        data={"sub": str(user.id)}, db=db, expires_delta=access_token_expires, token_type=TokenType.ACCESS.value
    )

    # Create a new refresh token
    refresh_token_expires = datetime.timedelta(days=settings.refresh_token_expire_days)
    refresh_token = create_token(
        data={"sub": str(user.id)}, db=db, expires_delta=refresh_token_expires, token_type=TokenType.REFRESH.value
    )

    # Invalidate the old refresh token
    token_crud.invalidate_token(
        db=db, token_jti=jti, token_type=TokenType.REFRESH.value
    )

    return access_token, refresh_token
