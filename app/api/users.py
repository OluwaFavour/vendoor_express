import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..dependencies import get_db, get_current_active_user, get_current_active_admin
from ..crud.user import (
    create_user as db_create_user,
    get_user_by_email as db_get_user_by_email,
    get_user as db_get_user,
)
from ..db.models import User as UserModel
from ..schemas.user import UserCreate, User
from ..core.debug import logger

router = APIRouter(prefix="/api/users", tags=["users"])


@router.post(
    "/",
    response_model=User,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user",
)
def create_user(
    user_scheme: UserCreate, db: Annotated[Session, Depends(get_db)]
) -> User:
    db_user = db_get_user_by_email(db, user_scheme.email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already in use",
        )
    try:
        new_user = db_create_user(db, user_scheme)
        logger.info(f"User created: {new_user.id}")
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
    else:
        return new_user


@router.get("/me", response_model=User, status_code=status.HTTP_200_OK)
def read_users_me(
    current_user: Annotated[UserModel, Depends(get_current_active_user)]
) -> User:
    return current_user


# TODO: This is an admin endpoint, add it to admin router
@router.get(
    "/{user_id}",
    response_model=User,
    dependencies=[Depends(get_current_active_admin)],
    status_code=status.HTTP_200_OK,
)
def read_user(
    user_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> User:
    db_user = db_get_user(db, user_id)
    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return db_user
