import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy.future import select

from ..dependencies import get_db, get_current_active_admin
from ..crud.user import get_user
from ..core.debug import logger
from ..db.enums import UserRoleType
from ..db.models import User as UserModel
from ..schemas.user import User

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get(
    "/users/{user_id}",
    response_model=User,
    dependencies=[Depends(get_current_active_admin)],
    status_code=status.HTTP_200_OK,
)
def read_user(
    user_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> User:
    db_user = get_user(db, user_id)
    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return db_user


@router.get(
    "/users/",
    response_model=list[User],
    dependencies=[Depends(get_current_active_admin)],
    status_code=status.HTTP_200_OK,
)
def read_users(
    db: Annotated[Session, Depends(get_db)],
    role: Annotated[Optional[UserRoleType], Query()] = None,
    is_active: Annotated[Optional[bool], Query()] = None,
    is_shop_owner: Annotated[Optional[bool], Query()] = None,
    skip: int = 0,
    limit: int = 100,
) -> list[User]:
    db_users = (
        db.execute(
            select(UserModel)
            .filter(
                UserModel.role == role if role else True,
                UserModel.is_active == is_active if is_active else True,
                UserModel.is_shop_owner == is_shop_owner if is_shop_owner else True,
            )
            .offset(skip)
            .limit(limit)
        )
        .scalars()
        .all()
    )
    return db_users


@router.put(
    "/users/{user_id}/admin",
    response_model=User,
    dependencies=[Depends(get_current_active_admin)],
    status_code=status.HTTP_200_OK,
    summary="Make a user an admin",
)
def make_user_admin(
    user_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> User:
    db_user = get_user(db, user_id)
    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    db_user.role = UserRoleType.ADMIN.value
    db.commit()
    return db_user
