from fastapi import APIRouter, Depends, HTTPException, status, Path

from sqlalchemy.orm import Session

from ..core.debug import logger
from ..db.models import Product as ProductModel
from ..schemas.products import Product


router = APIRouter(prefix="/api/products", tags=["products"])


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=Product,
    summary="Create a product",
)
def create_product():
    pass
