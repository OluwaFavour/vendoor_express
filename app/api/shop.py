from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..db.models import User as UserModel
from ..schemas.shop import Shop
from ..crud.shop import create_shop
from ..dependencies import get_current_active_user, get_db
from ..forms.shop import VendorProfileCreationForm


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
    shop = create_shop(db, vendor_profile, user)
    return shop
