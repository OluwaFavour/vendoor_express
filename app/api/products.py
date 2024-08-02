from datetime import datetime
from decimal import Decimal
from typing import Annotated, Optional
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Path,
    UploadFile,
    Query,
    Body,
)
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy.future import select

from ..core.debug import logger
from ..db.models import (
    Product as ProductModel,
    SubCategory as SubCategoryModel,
    User as UserModel,
)
from ..dependencies import get_db, get_current_active_verified_vendor
from ..forms.products import ProductCreateForm
from ..schemas.products import Product, Option, ProductPage
from ..schemas.user import SortField
from ..crud.products import (
    create_category,
    get_category,
    get_sub_category,
    create_sub_category,
    create_product,
    get_product_option,
    create_product_option,
    get_product,
)
from ..db.enums import FilterOperatorType
from ..core.utils import upload_image


router = APIRouter(prefix="/api/products", tags=["products"])


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=Product,
    summary="Add a product to shop",
)
def add_product(
    form: Annotated[ProductCreateForm, Depends()],
    current_vendor: Annotated[UserModel, Depends(get_current_active_verified_vendor)],
    db: Annotated[Session, Depends(get_db)],
):
    """
    Endpoint to add a new product to the shop.

    Parameters:
    - form: ProductCreateForm - The form data for creating the product.
    - current_vendor: UserModel - The currently authenticated and verified vendor.
    - db: Session - The database session.

    Returns:
    - The created product.
    """

    # Convert form data to dictionary and extract category name
    form_data = form.dict()
    category_name = form_data.pop("category")

    # Retrieve or create the category
    category = get_category(db, category_name)
    if not category:
        category = create_category(db, category_name)

    # Extract sub-category names and create sub-category list
    sub_categories_names = form_data.pop("sub_categories", None)
    sub_categories: list[SubCategoryModel] = []

    # Retrieve or create each sub-category and add to the list
    if sub_categories_names:
        for sub_category_name in sub_categories_names:
            sub_category = get_sub_category(db, category, sub_category_name)
            if not sub_category:
                sub_category = create_sub_category(db, sub_category_name, category.id)
            sub_categories.append(sub_category)

    # Extract options if provided
    options: Optional[list[Option]] = form_data.pop("options", None)

    # Handle media file uploads
    db_media: list[str] = []
    media: list[UploadFile] = form_data.pop("media")
    for media_file in media:
        try:
            product_name = form_data["name"]
            product_category = form_data["category"]
            media_file_url = upload_image(
                f"{current_vendor.id}/shop/products/{product_name}/{product_category}",
                media_file.file,
            )
            db_media.append(media_file_url)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # Join the media URLs into a single string separated by '||'
    form_data["media"] = "||".join(db_media)

    # Create a new product instance
    product = ProductModel(**form_data)
    product.category = category
    product.sub_categories.extend(sub_categories)

    try:
        # Add product to the database
        db_product = create_product(db, product)

        # Add options to the product if provided
        if options:
            for option in options:
                if not get_product_option(db, db_product, option.name):
                    create_product_option(db, db_product, option)

        # Associate the product with the current vendor's shop
        current_vendor.shop.products.append(db_product)
        db.commit()

    except IntegrityError as e:
        # Log and handle database integrity errors
        logger.error(f"Error adding product: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="There was an error adding the product. Please try again.",
        )

    # Return the created product
    return db_product


@router.get(
    "/",
    response_model=ProductPage,
    summary="Get all products",
)
def read_products(
    db: Annotated[Session, Depends(get_db)],
    price: Annotated[Optional[Decimal], Query()] = None,
    stock: Annotated[Optional[int], Query()] = None,
    stock_operator: Annotated[FilterOperatorType, Query()] = FilterOperatorType.LTE,
    price_operator: Annotated[FilterOperatorType, Query()] = FilterOperatorType.LTE,
    operator: Annotated[FilterOperatorType, Query()] = FilterOperatorType.AND,
    created_at_operator: Annotated[
        FilterOperatorType, Query()
    ] = FilterOperatorType.LTE,
    created_at_value: Annotated[Optional[datetime], Query()] = None,
    sort_by: Annotated[Optional[SortField], Body()] = None,
    search_query: Annotated[Optional[str], Query()] = None,
    skip: Annotated[int, Query(alias="offset", ge=0)] = 0,
    limit: Annotated[int, Query(alias="limit", ge=1, le=10)] = 10,
):
    """
    Endpoint to get all products.

    Parameters:
    - db: Session - The database session.
    - price: Decimal - Filter products by price.
    - stock: int - Filter products by stock.
    - stock_operator: FilterOperatorType - The operator to use for filtering by stock.
    - price_operator: FilterOperatorType - The operator to use for filtering by price.
    - operator: FilterOperatorType - The operator to use for filtering.
    - created_at_operator: FilterOperatorType - The operator to use for filtering by created date.
    - created_at_value: datetime - The value to use for filtering by created date.
    - sort_by: SortField - The field to sort by.
    - search_query: str - The search query to filter products by.
    - skip: int - The number of products to skip.
    - limit: int - The number of products to return.

    Returns:
    - A page of products.
    """

    # Initialize a list to store filter conditions
    filters = []

    # Helper function to add filter conditions
    def add_filter(attribute, operator, value):
        if value is not None:
            if operator == FilterOperatorType.LT:
                filters.append(attribute < value)
            elif operator == FilterOperatorType.GT:
                filters.append(attribute > value)
            elif operator == FilterOperatorType.LTE:
                filters.append(attribute <= value)
            elif operator == FilterOperatorType.GTE:
                filters.append(attribute >= value)
            elif operator == FilterOperatorType.NEQ:
                filters.append(attribute != value)
            elif operator == FilterOperatorType.LIKE:
                filters.append(attribute.ilike(f"%{value}%"))

    # Apply filters
    add_filter(ProductModel.price, price_operator, price)
    add_filter(ProductModel.stock, stock_operator, stock)
    add_filter(ProductModel.created_at, created_at_operator, created_at_value)

    # Apply search query
    if search_query:
        filters.append(ProductModel.name.ilike(f"%{search_query}%"))

    # Combine filters using the specified operator
    if operator == FilterOperatorType.AND:
        query = select(ProductModel).where(and_(*filters))
    elif operator == FilterOperatorType.OR:
        query = select(ProductModel).where(or_(*filters))
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The main operator must be AND or OR",
        )

    # Apply sorting
    if sort_by:
        sort_attr = getattr(ProductModel, sort_by, None)
        if sort_attr:
            query = query.order_by(sort_attr)

    # Calculate total products before pagination
    total_products = db.execute(query).scalars().count()

    # Apply pagination
    query = query.offset(skip).limit(limit)
    products = db.execute(query).scalars().all()

    # Calculate total pages
    total_pages = (total_products + limit - 1) // limit

    # Create and return the ProductPage response
    return ProductPage(
        page=skip // limit + 1,
        page_size=limit,
        total_pages=total_pages,
        total_products=total_products,
        products=products,
    )


@router.get(
    "/{product_id}",
    response_model=Product,
    summary="Get a product by ID",
)
def read_product(
    product_id: Annotated[UUID, Path(title="Product ID", description="The product ID")],
    db: Annotated[Session, Depends(get_db)],
):
    """
    Endpoint to get a product by its ID.

    Parameters:
    - product_id: UUID - The ID of the product to retrieve.
    - db: Session - The database session.

    Returns:
    - The product with the given ID.
    """
    product = get_product(db, product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    return product
