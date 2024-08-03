import re
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class AddressBase(BaseModel):
    full_name: str = Field(
        examples=["John Doe", "Jane Doe"], max_length=100, min_length=5
    )
    phone_number: str = Field(examples=["+2340123456789"], max_length=15, min_length=10)
    street_address: str = Field(
        examples=["24/26 nnpc road off akinola road, aboru"],
        max_length=100,
        min_length=5,
    )
    city: str = Field(examples=["Iyana-Paja", "Ibadan"], max_length=50, min_length=3)
    state: str = Field(examples=["Lagos", "Oyo"], max_length=50, min_length=3)
    country: str = Field(examples=["Nigeria"], max_length=50, min_length=3)
    postal_code: Optional[str] = Field(examples=["100001"], max_length=10, min_length=5)

    @field_validator("phone_number")
    def validate_phone_number(cls, v):
        phone_number_pattern = r"^\+?\d{10,15}$"
        if re.match(phone_number_pattern, v):
            return v
        raise ValueError("Invalid phone number format")

    @field_validator("full_name")
    def validate_full_name(cls, v):
        full_name_pattern = r"^[A-Za-z\s]{5,100}$"
        if re.match(full_name_pattern, v):
            return v
        raise ValueError("Invalid full name format")


class Address(AddressBase):
    id: UUID
    user_id: UUID
