import datetime
import jwt
from typing import Optional, Any
import uuid

from fastapi import Response, status
from fastapi.exceptions import HTTPException
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
        raise jwt.PyJWTError("Could not validate credentials")
    return user_id, jti


def create_token(
    data: dict,
    db: Session,
    token_type: str,
    expires_delta: datetime.timedelta,
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
    return encoded_jwt
