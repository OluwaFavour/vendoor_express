from decimal import Decimal
from typing import Optional, Annotated

from fastapi import Form, UploadFile, HTTPException, status

from ..schemas.products import Option


# class ProductBase(BaseModel):
#     model_config = ConfigDict(from_attributes=True)
#     name: str
#     description: str
#     price: decimal.Decimal
#     stock: int
#     media: HttpUrl
#     specification: Optional[str] = None
#     packaging: Optional[str] = None
#     category: Category
#     sub_category: Optional[SubCategory] = None


class ProductMediaValidator:
    @staticmethod
    def validate_media(
        media_file: UploadFile,
        allowed_formats: dict[str, str] = {
            "image/jpeg": "jpeg",
            "image/png": "png",
            "image/jpg": "jpg",
            "video/mp4": "mp4",
            "video/quicktime": "mov",
        },
    ) -> None:
        media_ext = media_file.filename.split(".")[-1].lower()
        media_format = media_file.content_type
        if (
            media_format not in allowed_formats
            or media_ext not in allowed_formats.values()
        ):
            raise ValueError(
                f"Only {', '.join(allowed_formats.values())} formats are allowed, check the format of {media_file.filename}"
            )


class ProductCreateForm:
    def __init__(
        self,
        name: Annotated[
            str, Form(title="Product name", description="Enter the product name")
        ],
        description: Annotated[
            str,
            Form(
                title="Product description", description="Enter the product description"
            ),
        ],
        price: Annotated[
            Decimal, Form(title="Product price", description="Enter the product price")
        ],
        stock: Annotated[
            int,
            Form(
                title="Product stock",
                description="Enter the number of products in stock",
            ),
        ],
        media: Annotated[
            list[UploadFile],
            Form(
                title="Product media", description="Upload product images and/or videos"
            ),
        ],
        category: Annotated[
            str,
            Form(title="Product category", description="Select the product category"),
        ],
        sub_categories: Annotated[
            Optional[list[str]],
            Form(
                title="Product sub-categories",
                description="Select the product sub-categories",
            ),
        ] = None,
        specification: Annotated[
            Optional[str],
            Form(
                title="Product specification",
                description="Enter the product specifications",
            ),
        ] = None,
        packaging: Annotated[
            Optional[str],
            Form(
                title="Product packaging",
                description="Enter the product packaging, i.e. what the product comes in and what it includes",
            ),
        ] = None,
        options: Annotated[
            Optional[list[Option]],
            Form(title="Product options", description="Enter the product options"),
        ] = None,
    ):
        self.name = name.lower()
        self.description = description
        self.price = price
        self.stock = stock
        self.media = media
        self.specification = specification
        self.packaging = packaging
        self.category = category.lower()
        self.sub_categories = (
            [sub_category.lower() for sub_category in sub_categories]
            if sub_categories
            else None
        )
        self.options = options
        self.validate_media_files()

    def validate_media_files(self):
        errors: list[dict[str, str]] = []
        for media_file in self.media:
            try:
                ProductMediaValidator.validate_media(media_file)
            except ValueError as e:
                errors.append({media_file.filename: str(e)})
        if errors:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=errors)

    def dict(self):
        values = {
            "name": self.name,
            "description": self.description,
            "price": self.price,
            "stock": self.stock,
            "media": self.media,
            "specification": self.specification,
            "packaging": self.packaging,
            "category": self.category,
            "sub_categories": self.sub_categories,
            "options": self.options,
        }
        return {k: v for k, v in values.items() if v is not None}
