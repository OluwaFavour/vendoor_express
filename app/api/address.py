from uuid import UUID
from typing import Optional, Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Path
from sqlalchemy.orm import Session
from sqlalchemy import exc

from ..crud import address as address_crud
from ..db.models import (
    Address as AddressModel,
    User as UserModel,
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

    address_data["user_id"] = user.id
    if address_data.get("is_default"):
        address_crud.remove_default_address(db, user.id)
    address_model = AddressModel(**address_data)
    try:
        address = address_crud.create_address(db, address_model)
    except exc.IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Address already exists",
        )
    return address


@router.get("/", response_model=list[address_schema.Address])
def get_addresses(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[UserModel, Depends(get_current_active_user)],
):
    """
    Get all addresses for the user.
    Args:
        db (Session): The database session.
        user (UserModel): The current active user.
    Returns:
        List[AddressModel]: The list of addresses.
    """
    addresses = address_crud.get_addresses(db, user.id)
    return addresses


@router.get("/{address_id}", response_model=address_schema.Address)
def get_address(
    address_id: Annotated[UUID, Path(title="Address ID")],
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[UserModel, Depends(get_current_active_user)],
) -> AddressModel:
    """
    Get an address by ID.
    Args:
        address_id (UUID): The ID of the address to get.
        db (Session): The database session.
        user (UserModel): The current active user.
    Returns:
        AddressModel: The address.
    Raises:
        HTTPException: If the address is not found.
    """
    address = address_crud.get_address(db, address_id)
    if address is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Address not found"
        )
    elif address.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this address",
        )
    return address


@router.delete("/{address_id}", response_model=None)
def delete_address(
    address_id: Annotated[UUID, Path(title="Address ID")],
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[UserModel, Depends(get_current_active_user)],
):
    """
    Delete an address by ID.
    Args:
        address_id (UUID): The ID of the address to delete.
        db (Session): The database session.
        user (UserModel): The current active user.
    """
    address = address_crud.get_address(db, address_id)
    if address is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Address not found"
        )
    elif address.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this address",
        )
    address_crud.delete_address(db, address_id)
    return None


@router.patch("/{address_id}/default", response_model=address_schema.Address)
def update_default_address(
    address_id: Annotated[UUID, Path(title="Address ID")],
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[UserModel, Depends(get_current_active_user)],
):
    """
    Update the default address.
    Args:
        address_id (UUID): The ID of the address to set as default.
        db (Session): The database session.
        user (UserModel): The current active user.
    Returns:
        AddressModel: The updated address.
    Raises:
        HTTPException: If the address is not found or does not belong to the user.
    """
    address = address_crud.update_default_address(db, user.id, address_id)
    if address is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Address not found"
        )
    return address


@router.delete("/{address_id}/default", response_model=None)
def remove_default_address(
    address_id: Annotated[UUID, Path(title="Address ID")],
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[UserModel, Depends(get_current_active_user)],
):
    """
    Remove the default address.
    Args:
        address_id (UUID): The ID of the address to remove as default.
        db (Session): The database session.
        user (UserModel): The current active user.
    """
    address = address_crud.get_address(db, address_id)
    if address is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Address not found"
        )
    elif address.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to remove this address as default",
        )
    address_crud.remove_default_address(db, user.id)
    return None
