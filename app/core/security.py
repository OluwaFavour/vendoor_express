import datetime
import jwt
from typing import Optional, Any
import uuid

from fastapi import Response
from sqlalchemy.orm import Session

from ..crud import user as user_crud
from ..crud import token as token_crud
from .config import password_context, settings
from .debug import logger
from ..db.models import User
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


def verify_token(token: str, credentials_exception: Exception) -> tuple[uuid.UUID, str]:
    try:
        payload: dict[str, Any] = jwt.decode(
            jwt=token,
            key=settings.secret_key,
            algorithms=[settings.algorithm],
        )
        jti = payload.get("jti")
        user_id = payload.get("sub")
        if jti is None or user_id is None:
            raise credentials_exception
        user_id = uuid.UUID(user_id)
    except jwt.PyJWTError:
        raise credentials_exception
    return user_id, jti


def create_token(
    data: dict,
    db: Session,
    token_type: str,
    expires_delta: datetime.timedelta,
    response: Optional[Response] = None,
) -> str:
    to_encode = data.copy()
    expire = datetime.datetime.now(datetime.UTC) + expires_delta
    to_encode.update({"exp": expire})
    to_encode.update({"jti": str(uuid.uuid4())})
    encoded_jwt = jwt.encode(
        to_encode, settings.secret_key, algorithm=settings.algorithm
    )
    # Store the token in the database
    token = token_crud.store_token(
        db=db,
        token_jti=to_encode["jti"],
        expires_at=expire,
        user_id=uuid.UUID(data["sub"]),
        token_type=token_type,
    )

    if token_type == TokenType.REFRESH.value:
        if response is not None:
            response.set_cookie(
                key="refresh_token",
                value=encoded_jwt,
                httponly=True,
                max_age=settings.refresh_token_expire_days * 24 * 60 * 60,  # in seconds
            )
        else:
            raise ValueError("Response object is required for refresh token")

    return encoded_jwt


def validate_token(token: str, token_type: str, db: Session) -> bool | User:
    """
    Validate the token
    ### Arguments
    token (str): The token
    token_type (str): The token type
    db (Session): The database session
    """
    try:
        user_id, jti = verify_token(token, jwt.PyJWTError)
    except jwt.PyJWTError:
        return False
    # Get the user from the database
    user = user_crud.get_user(db=db, user_id=user_id)
    if user is None:
        return False
    # Check the token in the database
    db_token = token_crud.get_token(db, jti)
    if db_token is None or db_token.user_id != user_id or db_token.is_active is False:
        return False
    if db_token.expires_at.replace(tzinfo=datetime.UTC) < datetime.datetime.now(
        datetime.UTC
    ):
        token_crud.invalidate_token(db=db, token_jti=jti, token_type=token_type)
        return False
    return user


def refresh_access_token(refresh_token: str, db: Session) -> str:
    """
    Refresh the access token
    ### Arguments
    refresh_token (str): The refresh token
    db (Session): The database session
    """
    user = validate_token(refresh_token, TokenType.REFRESH.value, db)
    if not user:
        raise jwt.PyJWTError("Invalid token")

    # Create a new access token
    access_token_expires = datetime.timedelta(
        minutes=settings.access_token_expire_minutes
    )
    access_token = create_token(
        data={"sub": str(user.id)},
        db=db,
        expires_delta=access_token_expires,
        token_type=TokenType.ACCESS.value,
    )

    return access_token
