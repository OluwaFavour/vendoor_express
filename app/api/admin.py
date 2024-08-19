from datetime import datetime, timedelta, UTC
import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from sqlalchemy import and_, or_, func
from sqlalchemy.orm import Session
from sqlalchemy.future import select

from fastapi_pagination import paginate, Params
from fastapi_pagination.links import Page

from ..dependencies import get_db, get_current_active_admin
from ..crud.user import get_user, update_user, get_all_users
from ..crud.shop import get_shop, get_all_shops
from ..core.config import settings
from ..core.debug import logger
from ..core.utils import delete_session_by_user_id, create_session, authenticate
from ..crud.session import (
    delete_session,
)
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


@router.post("/login", status_code=status.HTTP_200_OK)
def admin_login(
    user: Annotated[UserModel, Depends(authenticate)],
    db: Annotated[Session, Depends(get_db)],
    request: Request,
):
    if user.role != UserRoleType.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is not an admin",
        )
    # Get session data
    data = str(user.id)

    # Delete old session IDs if they exists
    delete_session_by_user_id(db, data)
    if "session_id" in request.cookies:
        old_session_id = request.cookies["session_id"]
        delete_session(db, uuid.UUID(old_session_id))

    # Get user agent and IP address
    user_agent = request.headers.get("User-Agent")
    ip_address = request.client.host

    # Generate session ID
    session_id = str(uuid.uuid4())
    # Store session
    expires_at = settings.session_expire_days
    expiry = datetime.now(UTC) + timedelta(days=expires_at)
    session_id = create_session(
        db=db,
        id=session_id,
        data=data,
        expires_at=expiry,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    request.session["session_id"] = session_id

    # Update user's first login status
    if user.is_first_login is None:
        update_user(db, user, is_first_login=True)
    else:
        update_user(db, user, is_first_login=False)

    # Create response
    response = JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "Successfully logged in",
            "user_agent": user_agent,
            "ip_address": ip_address,
            "is_first_login": user.is_first_login,
        },
    )
    # Store new session ID in cookie
    response.set_cookie(
        key=settings.session_cookie_name,
        value=session_id,
        httponly=True,
        samesite=settings.same_site,
        max_age=(expires_at * 24 * 60 * 60),
        secure=settings.https_only,
    )

    # Return response
    return response


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
    response_model=Page[User],
    dependencies=[Depends(get_current_active_admin)],
    status_code=status.HTTP_200_OK,
)
def read_users(
    db: Annotated[Session, Depends(get_db)],
    role: Annotated[
        Optional[UserRoleType],
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
    search_query: Annotated[
        Optional[str],
        Query(
            title="Search query",
            description="Search users by full name, email, or phone number",
        ),
    ] = None,
):
    filters = {
        "role": role.value if role else None,
        "is_active": is_active,
        "is_shop_owner": is_shop_owner,
        "search_query": search_query,
    }
    filters = {k: v for k, v in filters.items() if v is not None}
    try:
        users = get_all_users(db, **filters)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    return paginate(users, params=Params(page_size=10))


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
    response_model=Page[Shop],
    dependencies=[Depends(get_current_active_admin)],
    status_code=status.HTTP_200_OK,
)
def read_shops(
    db: Annotated[Session, Depends(get_db)],
    status: Annotated[Optional[VendorStatusType], Query()] = None,
    type: Annotated[Optional[ShopType], Query()] = None,
    category: Annotated[Optional[str], Query()] = None,
    search_query: Annotated[Optional[str], Query()] = None,
):
    filters = {
        "category": category,
        "status": status.value if status else None,
        "type": type.value if type else None,
        "name": search_query,
    }
    filters = {k: v for k, v in filters.items() if v is not None}
    try:
        shops = get_all_shops(db, **filters)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    return paginate(shops, params=Params(page_size=10))


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
