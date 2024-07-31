from datetime import datetime
import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import and_, or_, func
from sqlalchemy.orm import Session
from sqlalchemy.future import select

from ..dependencies import get_db, get_current_active_admin
from ..crud.user import get_user
from ..crud.shop import get_shop
from ..core.debug import logger
from ..db.enums import FilterOperatorType, UserRoleType, VendorStatusType, SortDirection
from ..db.models import User as UserModel
from ..schemas.user import User, Page

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
    response_model=Page,
    dependencies=[Depends(get_current_active_admin)],
    status_code=status.HTTP_200_OK,
)
def read_users(
    db: Session = Depends(get_db),
    roles: list[UserRoleType] = Query(None),
    is_active: list[bool] = Query(None),
    is_shop_owner: list[bool] = Query(None),
    operator: FilterOperatorType = Query(FilterOperatorType.AND),
    created_at_operator: FilterOperatorType = Query(FilterOperatorType.AND),
    created_at_value: Optional[datetime] = Query(None),
    sort_by: list[tuple[str, SortDirection]] = Query(None),
    search_query: Optional[str] = Query(None),
    skip: Annotated[int, Query(alias="offset", ge=0)] = 0,
    limit: Annotated[int, Query(alias="limit", ge=1, le=10)] = 10,
) -> list[User]:
    filters = []

    if roles:
        filters.append(UserModel.role.in_(roles))
    if is_active is not None:
        filters.append(UserModel.is_active.in_(is_active))
    if is_shop_owner is not None:
        filters.append(UserModel.is_shop_owner.in_(is_shop_owner))

    if created_at_operator == FilterOperatorType.LT:
        filters.append(UserModel.created_at < created_at_value)
    elif created_at_operator == FilterOperatorType.GT:
        filters.append(UserModel.created_at > created_at_value)
    elif created_at_operator == FilterOperatorType.LTE:
        filters.append(UserModel.created_at <= created_at_value)
    elif created_at_operator == FilterOperatorType.GTE:
        filters.append(UserModel.created_at >= created_at_value)
    elif created_at_operator == FilterOperatorType.NEQ:
        filters.append(UserModel.created_at != created_at_value)
    elif created_at_operator == FilterOperatorType.LIKE:
        filters.append(UserModel.created_at.like(f"%{created_at_value}%"))

    if sort_by:
        sort_expressions = [
            (
                getattr(UserModel, field).asc()
                if direction == SortDirection.ASC
                else getattr(UserModel, field).desc()
            )
            for field, direction in sort_by
        ]
        query = db.query(UserModel).order_by(*sort_expressions)
    else:
        query = db.query(UserModel)

    if search_query:
        filters.append(UserModel.full_name.ilike(f"%{search_query}%"))
        filters.append(UserModel.email.ilike(f"%{search_query}%"))
        filters.append(UserModel.phone_number.ilike(f"%{search_query}%"))

    if filters:
        if operator == FilterOperatorType.AND:
            query = query.filter(*filters)
        elif operator == FilterOperatorType.OR:
            query = query.filter(db.or_(*filters))

    total_count = query.count()
    total_pages = (total_count + limit - 1) // limit
    page = skip // limit + 1
    users = query.offset(skip).limit(limit).all()

    return Page(
        page=page,
        page_size=limit,
        total_pages=total_pages,
        total_users=total_count,
        users=users,
    )


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
