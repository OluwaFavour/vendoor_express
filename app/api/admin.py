from datetime import datetime
import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy import and_, or_, func
from sqlalchemy.orm import Session
from sqlalchemy.future import select

from ..dependencies import get_db, get_current_active_admin
from ..crud.user import get_user
from ..crud.shop import get_shop
from ..core.debug import logger
from ..db.enums import (
    FilterOperatorType,
    UserRoleType,
    VendorStatusType,
    SortDirection,
    ShopType,
    WantedHelpType,
)
from ..db.models import User as UserModel, Shop as ShopModel
from ..schemas.user import User, UserPage, SortField
from ..schemas.shop import Shop, ShopPage

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
    response_model=UserPage,
    dependencies=[Depends(get_current_active_admin)],
    status_code=status.HTTP_200_OK,
)
def read_users(
    db: Annotated[Session, Depends(get_db)],
    roles: Annotated[
        Optional[list[UserRoleType]],
        Query(
            title="User roles",
            description="Filter users by roles, e.g. roles=admin&roles=vendor",
        ),
    ] = None,
    is_active: Annotated[
        Optional[bool],
        Query(
            title="Is active",
            description="Filter users by active status",
        ),
    ] = None,
    is_shop_owner: Annotated[
        Optional[bool],
        Query(
            title="Is shop owner",
            description="Filter users by shop owner status",
        ),
    ] = None,
    operator: Annotated[FilterOperatorType, Query()] = FilterOperatorType.AND,
    created_at_operator: Annotated[
        FilterOperatorType, Query()
    ] = FilterOperatorType.LTE,
    created_at_value: Annotated[Optional[datetime], Query()] = None,
    sort_by: Annotated[Optional[SortField], Body()] = None,
    search_query: Annotated[
        Optional[str],
        Query(
            title="Search query",
            description="Search users by full name, email, or phone number",
        ),
    ] = None,
    skip: Annotated[int, Query(alias="offset", ge=0)] = 0,
    limit: Annotated[int, Query(alias="limit", ge=1, le=10)] = 10,
) -> UserPage:
    filters = []

    if roles:
        filters.append(UserModel.role.in_(roles))
    if is_active is not None:
        filters.append(UserModel.is_active.is_(is_active))
    if is_shop_owner is not None:
        filters.append(UserModel.is_shop_owner.is_(is_shop_owner))

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
        sort_expression = (
            getattr(UserModel, sort_by.field).asc()
            if sort_by.direction == SortDirection.ASC
            else getattr(UserModel, sort_by.field).desc()
        )
        query = select(UserModel).order_by(*sort_expression)
    else:
        query = select(UserModel)

    if search_query:
        filters.append(UserModel.full_name.ilike(f"%{search_query}%"))
        filters.append(UserModel.email.ilike(f"%{search_query}%"))
        filters.append(UserModel.phone_number.ilike(f"%{search_query}%"))

    if filters:
        if operator == FilterOperatorType.AND:
            query = query.filter(*filters)
        elif operator == FilterOperatorType.OR:
            query = query.filter(or_(*filters))

    total_count = db.execute(select(func.count(UserModel.id)).filter(*filters)).scalar()
    total_pages = (total_count + limit - 1) // limit
    page = skip // limit + 1
    users = db.execute(query.offset(skip).limit(limit)).scalars().all()

    return UserPage(
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


@router.get(
    "/shops/",
    response_model=ShopPage,
    dependencies=[Depends(get_current_active_admin)],
    status_code=status.HTTP_200_OK,
)
def read_shops(
    db: Annotated[Session, Depends(get_db)],
    types: Annotated[Optional[list[ShopType]], Query()] = None,
    categories: Annotated[Optional[list[str]], Query()] = None,
    wanted_helps: Annotated[Optional[list[WantedHelpType]], Query()] = None,
    statuses: Annotated[Optional[list[VendorStatusType]], Query()] = None,
    operator: Annotated[FilterOperatorType, Query()] = FilterOperatorType.AND,
    created_at_operator: Annotated[
        FilterOperatorType, Query()
    ] = FilterOperatorType.LTE,
    created_at_value: Annotated[Optional[datetime], Query()] = None,
    sort_by: Annotated[Optional[SortField], Body()] = None,
    search_query: Annotated[Optional[str], Query()] = None,
    skip: Annotated[int, Query(alias="offset", ge=0)] = 0,
    limit: Annotated[int, Query(alias="limit", ge=1, le=10)] = 10,
) -> ShopPage:
    filters = []

    if types:
        filters.append(ShopModel.type.in_(types))
    if categories:
        filters.append(ShopModel.category.in_(categories))
    if wanted_helps:
        filters.append(ShopModel.wanted_help.in_(wanted_helps))
    if statuses:
        filters.append(ShopModel.status.in_(statuses))

    if created_at_operator == FilterOperatorType.LT:
        filters.append(ShopModel.created_at < created_at_value)
    elif created_at_operator == FilterOperatorType.GT:
        filters.append(ShopModel.created_at > created_at_value)
    elif created_at_operator == FilterOperatorType.LTE:
        filters.append(ShopModel.created_at <= created_at_value)
    elif created_at_operator == FilterOperatorType.GTE:
        filters.append(ShopModel.created_at >= created_at_value)
    elif created_at_operator == FilterOperatorType.NEQ:
        filters.append(ShopModel.created_at != created_at_value)
    elif created_at_operator == FilterOperatorType.LIKE:
        filters.append(ShopModel.created_at.like(f"%{created_at_value}%"))

    if sort_by:
        sort_expression = (
            getattr(ShopModel, sort_by.field).asc()
            if sort_by.direction == SortDirection.ASC
            else getattr(ShopModel, sort_by.field).desc()
        )
        query = select(ShopModel).order_by(*sort_expression)
    else:
        query = select(ShopModel)

    if search_query:
        filters.append(ShopModel.name.ilike(f"%{search_query}%"))
        filters.append(ShopModel.email.ilike(f"%{search_query}%"))
        filters.append(ShopModel.phone_number.ilike(f"%{search_query}%"))

    if filters:
        if operator == FilterOperatorType.AND:
            query = query.filter(*filters)
        elif operator == FilterOperatorType.OR:
            query = query.filter(or_(*filters))

    total_count = db.execute(select(func.count(ShopModel.id)).filter(*filters)).scalar()
    total_pages = (total_count + limit - 1) // limit
    page = skip // limit + 1
    shops = db.execute(query.offset(skip).limit(limit)).scalars().all()

    return ShopPage(
        page=page,
        page_size=limit,
        total_pages=total_pages,
        total_users=total_count,
        shops=shops,
    )


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
