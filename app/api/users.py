from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..dependencies import get_db
from ..crud.user import (
    create_user as db_create_user,
    get_user_by_email as db_get_user_by_email,
)
from ..schemas.user import UserCreate, User
from ..core.debug import logger

router = APIRouter(prefix="/api/users", tags=["users"])


@router.post("/", response_model=User, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate, db: Annotated[Session, Depends(get_db)]) -> User:
    db_user = db_get_user_by_email(db, user.email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already in use",
        )
    try:
        new_user = db_create_user(db, user)
        logger.info(f"User created: {new_user.id}")
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
    else:
        return new_user
