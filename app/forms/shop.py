from typing import Annotated, Any

from fastapi import Form, UploadFile, File
from pydantic import EmailStr

from ..db.enums import UserRoleType, ProofOfIdentityType, ShopType, WantedHelpType


class VendorProfileCreationValidator:
    @staticmethod
    def validate_image(
        image: UploadFile,
        field_name: str,
        allowed_formats: dict[str, str] = {
            "image/jpeg": "jpeg",
            "image/png": "png",
            "image/jpg": "jpg",
        },
    ) -> None:
        image_ext = image.filename.split(".")[-1]
        image_format = image.content_type
        if (
            image_format not in allowed_formats.keys()
            or image_ext not in allowed_formats.values()
        ):
            raise ValueError(
                "Only jpeg, jpg and png formats are allowed, check the image format of the {}".format(
                    field_name
                )
            )


class VendorProfileCreationForm:
    def __init__(
        self,
        user_phone_number: Annotated[
            str,
            Form(
                title="Phone Number",
                description="Phone number of the user",
            ),
        ],
        proof_of_identity_type: Annotated[
            ProofOfIdentityType,
            Form(
                title="Proof of Identity Type",
                description="Type of proof of identity",
            ),
        ],
        proof_of_identity_image: Annotated[
            UploadFile,
            File(
                title="Proof of Identity Image",
                description="Image of the proof of identity",
            ),
        ],
        business_registration_certificate_image: Annotated[
            UploadFile,
            File(
                title="Business Registration Certificate Image",
                description="Image of the business registration certificate",
            ),
        ],
        logo: Annotated[
            UploadFile, File(title="Shop Logo", description="Logo of the shop")
        ],
        name: Annotated[str, Form(title="Shop Name", description="Name of the shop")],
        description: Annotated[
            str, Form(title="Shop Details", description="Details of the shop")
        ],
        email: Annotated[
            EmailStr, Form(title="Shop Email", description="Email of the shop")
        ],
        phone_number: Annotated[
            str, Form(title="Shop Phone", description="Phone number of the shop")
        ],
        type: Annotated[
            ShopType, Form(title="Shop Type", description="Type of the shop")
        ],
        category: Annotated[
            str, Form(title="Shop Category", description="Category of the shop")
        ],
        wanted_help: Annotated[
            WantedHelpType, Form(title="Wanted Help", description="Type of help wanted")
        ],
        role: Annotated[
            UserRoleType, Form(title="Role", description="Role of the user")
        ] = UserRoleType.VENDOR,
    ):
        images = {
            "proof_of_identity_image": proof_of_identity_image,
            "business_registration_certificate_image": business_registration_certificate_image,
            "logo": logo,
        }
        for field, image in images.items():
            VendorProfileCreationValidator.validate_image(image, field)
        if role.name != "VENDOR":
            raise ValueError("Only VENDOR role is allowed during shop creation")
        self.proof_of_identity_image = proof_of_identity_image
        self.logo = logo
        self.business_registration_certificate_image = (
            business_registration_certificate_image
        )
        self.user_phone_number = user_phone_number
        self.proof_of_identity_type = proof_of_identity_type
        self.role = role.value
        self.name = name
        self.description = description
        self.email = email
        self.phone_number = phone_number
        self.type = type
        self.category = category
        self.wanted_help = wanted_help

    def dict(self) -> dict[str, Any]:
        return {
            "user_phone_number": self.user_phone_number,
            "proof_of_identity_type": self.proof_of_identity_type,
            "proof_of_identity_image": self.proof_of_identity_image,
            "business_registration_certificate_image": self.business_registration_certificate_image,
            "logo": self.logo,
            "name": self.name,
            "description": self.description,
            "email": self.email,
            "phone_number": self.phone_number,
            "type": self.type,
            "category": self.category,
            "wanted_help": self.wanted_help,
            "user_role": self.role,
        }
