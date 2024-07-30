import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session
from sqlalchemy.future import select

from ..dependencies import get_db, get_current_active_admin
from ..crud.user import get_user
from ..crud.shop import get_shop
from ..core.debug import logger
from ..db.enums import OperatorType, UserRoleType, VendorStatusType
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
    db: Session = Depends(get_db),
    role: Optional[UserRoleType] = Query(None),
    is_active: Optional[bool] = Query(None),
    is_shop_owner: Optional[bool] = Query(None),
    operator: OperatorType = Query(OperatorType.AND),
    skip: int = 0,
    limit: int = 100,
) -> list[User]:
    if operator not in [OperatorType.AND, OperatorType.OR]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid operator"
        )
    filters = []
    if role is not None:
        filters.append(UserModel.role == role)
    if is_active is not None:
        filters.append(UserModel.is_active == is_active)
    if is_shop_owner is not None:
        filters.append(UserModel.is_shop_owner == is_shop_owner)

    if not filters:
        final_filter = (
            and_(True, *filters)
            if operator == OperatorType.AND
            else or_(True, *filters)
        )

    query = select(UserModel).filter(final_filter).offset(skip).limit(limit)

    db_users = db.execute(query).scalars().all()

    return db_users


@router.put(
    "/users/{user_id}/make-admin",
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


@router.put(
    "/shops/{shop_id}/verify",
    dependencies=[Depends(get_current_active_admin)],
    status_code=status.HTTP_200_OK,
    summary="Verify a shop",
)
def verify_shop(
    shop_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
):
    db_shop = get_shop(db, shop_id)
    if db_shop is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shop not found",
        )
    if db_shop.status == VendorStatusType.VERIFIED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Shop is already verified",
        )
    db_shop.status = VendorStatusType.VERIFIED.value
    db.commit()
    return db_shop
