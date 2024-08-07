from datetime import datetime
import decimal
from typing import Optional
import uuid

from pydantic import BaseModel, ConfigDict, HttpUrl, field_serializer


class CategoryBase(BaseModel):
    name: str


class Category(CategoryBase):
    id: uuid.UUID


class SubCategoryBase(BaseModel):
    name: str
    category_id: uuid.UUID


class SubCategory(SubCategoryBase):
    id: uuid.UUID


class Option(BaseModel):
    name: str
    value: str

    @field_serializer("name")
    def serialize_name(name):
        return name.lower()


class ProductBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str
    description: str
    price: decimal.Decimal
    stock: int
    media: HttpUrl
    specification: Optional[str] = None
    packaging: Optional[str] = None
    category: Category
    sub_category: Optional[SubCategory] = None
    options: Optional[list[Option]] = None


class Product(ProductBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class ProductPage(BaseModel):
    page: int
    page_size: int
    total_pages: int
    total_products: int
    products: list[Product]
