from typing import Optional
from uuid import UUID

from sqlalchemy.exc import ArgumentError
from sqlalchemy.future import select
from sqlalchemy.orm import Session

from ..db.models import Product, Category, SubCategory, ProductOption, Shop


def create_category(db: Session, name: str) -> Category:
    """Create a new category."""
    db_category = Category(name=name)
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category


def list_categories(db: Session) -> list[Category]:
    """List all categories."""
    return db.execute(select(Category)).scalars().all()


def get_category(db: Session, name: str) -> Optional[Category]:
    """Get a category by name."""
    return db.execute(
        select(Category).filter(Category.name == name)
    ).scalar_one_or_none()


def get_sub_category(
    db: Session, category: Category, name: str
) -> Optional[SubCategory]:
    """Get a sub-category by name under a specific category."""
    return db.execute(
        select(SubCategory).filter(
            SubCategory.category_id == category.id, SubCategory.name == name
        )
    ).scalar_one_or_none()


def create_sub_category(db: Session, name: str, category_id: UUID) -> SubCategory:
    """Create a new sub-category."""
    db_sub_category = SubCategory(name=name, category_id=category_id)
    db.add(db_sub_category)
    db.commit()
    db.refresh(db_sub_category)
    return db_sub_category


def list_sub_categories(db: Session, category_name: str) -> list[SubCategory]:
    """List all sub-categories under a specific category."""
    return (
        db.execute(
            select(SubCategory).filter(SubCategory.category.has(name=category_name))
        )
        .scalars()
        .all()
    )


def add_category_to_product(
    db: Session, product: Product, category: Category
) -> Product:
    """Assign a category to a product."""
    product.category = category
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def add_sub_category_to_product(
    db: Session, product: Product, sub_category: SubCategory
) -> Product:
    """Assign a sub-category to a product."""
    if sub_category.category_id != product.category_id:
        raise ArgumentError("Sub-category does not belong to the product's category")
    product.sub_categories.append(sub_category)
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def delete_category(db: Session, name: str) -> None:
    """Delete a category by name."""
    db_category = get_category(db, name)
    if db_category is None:
        raise ValueError("Category not found")
    db.delete(db_category)
    db.commit()


def delete_sub_category(db: Session, name: str) -> None:
    """Delete a sub-category by name."""
    db_sub_category = db.execute(
        select(SubCategory).filter(SubCategory.name == name)
    ).scalar_one_or_none()
    if db_sub_category is None:
        raise ValueError("Sub-category not found")
    db.delete(db_sub_category)
    db.commit()


def delete_sub_categories(db: Session, category_name: str) -> None:
    """Delete all sub-categories under a specific category."""
    db_sub_categories = list_sub_categories(db, category_name)
    if not db_sub_categories:
        raise ValueError("Sub-categories not found")
    for db_sub_category in db_sub_categories:
        db.delete(db_sub_category)
    db.commit()


def get_product_option(
    db: Session, name: str, product_id: UUID
) -> Optional[ProductOption]:
    """Get a product option by product ID."""
    return db.execute(
        select(ProductOption).filter(
            ProductOption.product_id == product_id, ProductOption.name == name
        )
    ).scalar_one_or_none()


def create_product_option(
    db: Session, name: str, value: str, product_id: UUID
) -> ProductOption:
    """Create a new product option."""
    db_product_option = ProductOption(name=name, value=value, product_id=product_id)
    db.add(db_product_option)
    db.commit()
    db.refresh(db_product_option)
    return db_product_option


def delete_product_option(db: Session, product: Product) -> None:
    """Delete a product option."""
    db_product_option = db.execute(
        select(ProductOption).filter(ProductOption.product_id == product.id)
    ).scalar_one_or_none()
    if db_product_option is None:
        raise ValueError("Product option not found")
    db.delete(db_product_option)
    db.commit()


def delete_product_options(db: Session, product: Product) -> None:
    """Delete all options of a product."""
    db_product_options = product.options
    if not db_product_options:
        raise ValueError("Product options not found")
    for db_product_option in db_product_options:
        db.delete(db_product_option)
    db.commit()


def create_product(db: Session, product: Product) -> Product:
    """Create a new product."""
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def get_product(db: Session, product_id: UUID) -> Optional[Product]:
    """Get a product by ID."""
    return db.execute(
        select(Product).filter(Product.id == product_id)
    ).scalar_one_or_none()


def list_products(db: Session) -> list[Product]:
    """List all products."""
    return db.execute(select(Product)).scalars().all()


def disable_product(db: Session, product: Product) -> Product:
    """Disable a product."""
    product.disabled = True
    db.commit()
    db.refresh(product)
    return product


def delete_product(db: Session, product: Product) -> None:
    """Delete a product."""
    db.delete(product)
    db.commit()
