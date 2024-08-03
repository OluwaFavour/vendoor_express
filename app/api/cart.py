from decimal import Decimal
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, Form
from sqlalchemy.orm import Session

from ..crud import cart
from ..db.models import User as UserModel, CartItem as CartItemModel
from ..dependencies import get_db, get_current_active_user
from ..schemas.cart import Cart, CartSummary

router = APIRouter(tags=["cart"], prefix="/api/users/me/cart")


@router.post(
    "/{product_id}",
    response_model=Cart,
    status_code=status.HTTP_201_CREATED,
    summary="Add product to cart",
)
def add_product_to_cart(
    product_id: Annotated[UUID, Path(title="Product ID")],
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[UserModel, Depends(get_current_active_user)],
    quantity: Annotated[
        Optional[int],
        Query(title="Quantity of product", ge=1, le=100),
    ] = None,
) -> Cart:
    """
    Add a product to the user's cart.

    Args:
        product_id (UUID): The ID of the product to add.
        db (Session): The database session.
        user (UserModel): The current user.
        quantity (int, optional): The quantity of the product to add. Defaults to None.

    Returns:
        Cart: The updated cart item, or the newly created cart item.

    Raises:
        None

    """

    # Check if the product is already in the cart
    if (
        cart_item := cart.get_cart_item_by_product_id(db, user, product_id)
    ) is not None:
        # If the product is already in the cart, update the quantity
        cart_item.quantity += quantity or 1
        db.commit()
        db.refresh(cart_item)
        return cart_item

    # If the product is not in the cart, add it and return the new cart item
    return cart.add_product_to_cart(db, product_id, user, quantity)


@router.delete(
    "/{cart_item_id}", response_model=None, status_code=status.HTTP_204_NO_CONTENT
)
def remove_product_from_cart(
    cart_item_id: Annotated[UUID, Path(title="Cart Item ID")],
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[UserModel, Depends(get_current_active_user)],
) -> None:
    """
    Remove a product from the user's cart.

    Args:
        cart_item_id (UUID): The ID of the cart item to remove.
        db (Session): The database session.
        user (UserModel): The current user.

    Returns:
        None

    Raises:
        HTTPException: 404 - Not Found if the cart item is not found.
        HTTPException: 403 - Forbidden if the user does not have permission to access the cart item.

    """
    if (cart_item := cart.get_cart_item(db, cart_item_id)) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found"
        )

    if cart_item.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this cart item",
        )

    cart.remove_product_from_cart(db, cart_item)


@router.get(
    "/",
    response_model=list[Cart],
    summary="Get the user's cart",
    status_code=status.HTTP_200_OK,
)
def read_cart(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[UserModel, Depends(get_current_active_user)],
) -> list[Cart]:
    """
    Get the user's cart.

    Args:
        db (Session, optional): The database session. Defaults to Depends(get_db).
        user (UserModel, optional): The current user. Defaults to Depends(get_current_active_user).

    Returns:
        list[Cart]: The user's cart.

    """
    return cart.get_cart_items(db, user)


@router.get(
    "/summary",
    response_model=CartSummary,
    summary="Get the user's cart summary",
    status_code=status.HTTP_200_OK,
)
def read_cart_summary(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[UserModel, Depends(get_current_active_user)],
) -> CartSummary:
    """
    Get the user's cart summary.

    Args:
        db (Session, optional): The database session. Defaults to Depends(get_db).
        user (UserModel, optional): The current user. Defaults to Depends(get_current_active_user).

    Returns:
        Decimal: The user's cart summary.

    """
    price, count = cart.get_cart_summary(db, user)

    return CartSummary(
        user_id=user.id,
        total_items=count,
        total_cost=price,
    )


@router.put(
    "/{cart_item_id}",
    response_model=Cart,
    summary="Update the quantity of a product in the user's cart",
    status_code=status.HTTP_200_OK,
)
def update_cart_item_quantity(
    cart_item_id: Annotated[UUID, Path(title="Cart Item ID")],
    quantity: Annotated[
        int,
        Form(title="Quantity of product", ge=1, le=100),
    ],
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[UserModel, Depends(get_current_active_user)],
) -> Cart:
    """
    Update the quantity of a product in the user's cart.

    Args:
        cart_item_id (UUID): The ID of the cart item to update.
        quantity (int): The new quantity of the product.
        db (Session): The database session.
        user (UserModel): The current user.

    Returns:
        Cart: The updated cart item.

    Raises:
        HTTPException: 404 - Not Found if the cart item is not found.
        HTTPException: 403 - Forbidden if the user does not have permission to access the cart item.

    """
    if (cart_item := cart.get_cart_item(db, cart_item_id)) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found"
        )

    if cart_item.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this cart item",
        )

    return cart.update_cart_item_quantity(db, cart_item, quantity)
