import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Path
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from ..core.debug import logger
from ..db.models import User as UserModel
from ..schemas.shop import Shop, StaffMember
from ..crud.shop import (
    create_shop,
    update_shop,
    add_staff_to_shop,
    update_shop_staff,
    get_shop_staff,
    get_shop_staffs,
)
from ..dependencies import (
    get_current_active_user,
    get_db,
    get_current_active_verified_vendor,
    get_current_active_vendor,
)
from ..forms.shop import VendorProfileCreationForm, ShopUpdateForm, StaffMemberForm


router = APIRouter(prefix="/api/shop", tags=["shop"])


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=Shop,
    summary="Create a vendor profile",
)
def create_vendor_profile(
    db: Annotated[Session, Depends(get_db)],
    vendor_profile: Annotated[VendorProfileCreationForm, Depends()],
    user: Annotated[UserModel, Depends(get_current_active_user)],
):
    try:
        shop = create_shop(db, vendor_profile, user)
        return shop
    except IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e.orig),
        )


@router.get(
    "/me",
    response_model=Shop,
    status_code=status.HTTP_200_OK,
    summary="Get vendor profile",
)
def read_shop_me(
    current_vendor: Annotated[UserModel, Depends(get_current_active_vendor)]
) -> Shop:
    return current_vendor.shop


@router.patch(
    "/me",
    response_model=Shop,
    status_code=status.HTTP_200_OK,
    summary="Update vendor profile",
)
def update_vendor_profile(
    db: Annotated[Session, Depends(get_db)],
    form_data: Annotated[ShopUpdateForm, Depends()],
    current_vendor: Annotated[UserModel, Depends(get_current_active_verified_vendor)],
):
    try:
        shop = update_shop(db, current_vendor.shop, **form_data.dict())
        return shop
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e.orig),
        )


@router.post("/me/staffs/", status_code=status.HTTP_201_CREATED, summary="Add a staff")
def add_staff(
    db: Annotated[Session, Depends(get_db)],
    form_data: Annotated[StaffMemberForm, Depends()],
    current_vendor: Annotated[UserModel, Depends(get_current_active_verified_vendor)],
) -> StaffMember:
    try:
        shop = current_vendor.shop
        staff = add_staff_to_shop(db, shop, **form_data.dict())
        return staff
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.patch(
    "/me/staffs/{staff_id}",
    response_model=StaffMember,
    status_code=status.HTTP_200_OK,
    summary="Update staff",
)
def update_staff(
    db: Annotated[Session, Depends(get_db)],
    form_data: Annotated[StaffMemberForm, Depends()],
    staff_id: Annotated[uuid.UUID, Path(title="Staff ID", description="Staff ID")],
    current_vendor: Annotated[UserModel, Depends(get_current_active_verified_vendor)],
):
    try:
        staff = get_shop_staff(db, current_vendor.shop, staff_id)
        if staff is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Staff not found",
            )
        update_shop_staff(db, staff, **form_data.dict())
        return staff
    except IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e.orig),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except HTTPException as e:
        raise e


@router.get(
    "/me/staffs/",
    response_model=list[StaffMember],
    status_code=status.HTTP_200_OK,
    summary="Get all staffs",
)
def get_staffs(
    db: Annotated[Session, Depends(get_db)],
    current_vendor: Annotated[UserModel, Depends(get_current_active_verified_vendor)],
):
    staffs = get_shop_staffs(db, current_vendor.shop)
    return staffs
