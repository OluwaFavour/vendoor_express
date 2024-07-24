import datetime
import jwt
from typing import Optional
import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from .models import User
from .crud import get_user_by_email, store_token
from .settings import password_context, get_settings


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


def create_access_token(
    data: dict, db: Session, expires_delta: Optional[datetime.timedelta] = None
) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.datetime.now(datetime.UTC) + expires_delta
    else:
        expire = datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=15)
    to_encode.update({"exp": expire})
    to_encode.update({"jti": str(uuid.uuid4())})
    encoded_jwt = jwt.encode(
        to_encode, get_settings().secret_key, algorithm=get_settings().algorithm
    )

    # Get the user from the database
    user = get_user_by_email(db, data["sub"])  # data["sub"] is the email
    # Store the token in the database
    store_token(db=db, token_jti=to_encode["jti"], expires_at=expire, user=user)

    return encoded_jwt


def authenticate(db: Session, email: str, password: str) -> User:
    user = get_user_by_email(db, email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"User with email '{email}' does not exist.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Password is incorrect.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
