from datetime import datetime
import decimal
from typing import Optional
import uuid

from pydantic import BaseModel, ConfigDict, HttpUrl


class CategoryBase(BaseModel):
    name: str


class Category(CategoryBase):
    id: uuid.UUID


class SubCategoryBase(BaseModel):
    name: str
    category_id: uuid.UUID


class SubCategory(SubCategoryBase):
    id: uuid.UUID


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


class Product(ProductBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
