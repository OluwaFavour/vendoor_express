from uuid import UUID
from typing import Optional, Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..crud import address as address_crud
from ..db.models import (
    Address as AddressModel,
    User as UserModel,
    DefaultAddress as DefaultAddressModel,
)
from ..dependencies import get_db, get_current_active_user
from ..schemas import address as address_schema
from ..forms.address import AddressForm

router = APIRouter(prefix="/api/users/me/addresses", tags=["addresses"])


@router.post("/", response_model=address_schema.Address)
def create_address(
    address_form: Annotated[AddressForm, Depends()],
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_active_user),
):
    """
    Create a new address for the user.
    Args:
        address_form (AddressForm): The form containing the address data.
        db (Session, optional): The database session. Defaults to Depends(get_db).
        user (UserModel, optional): The current active user. Defaults to Depends(get_current_active_user).
    Returns:
        AddressModel: The created address.
    Raises:
        HTTPException: If there is a value error while processing the address form.
    """
    try:
        address_data = address_form()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    set_as_default = address_data.pop("set_as_default", False)

    address_data["user_id"] = user.id
    address_model = AddressModel(**address_data)
    address = address_crud.create_address(db, address_model)

    if set_as_default:
        default_address = address_crud.create_default_address(db, user.id, address.id)
        user.default_address = default_address
        db.commit()
        db.refresh(user)

    return address
