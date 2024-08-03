import re
from typing import Optional, Annotated

from fastapi import Form


class AddressForm:
    def __init__(
        self,
        full_name: Annotated[
            str, Form(example="John Doe", max_length=100, min_length=5)
        ],
        phone_number: Annotated[
            str, Form(example="+2340123456789", max_length=15, min_length=10)
        ],
        street_address: Annotated[
            str,
            Form(
                example="24/26 nnpc road off akinola road, aboru",
                max_length=100,
                min_length=5,
            ),
        ],
        city: Annotated[str, Form(example="Iyana-Paja", max_length=50, min_length=3)],
        state: Annotated[str, Form(example="Lagos", max_length=50, min_length=3)],
        country: Annotated[str, Form(example="Nigeria", max_length=50, min_length=3)],
        postal_code: Annotated[
            Optional[str], Form(example="100001", max_length=10, min_length=5)
        ] = None,
        set_as_default: Annotated[bool, Form()] = False,
    ):
        self.full_name = full_name
        self.phone_number = phone_number
        self.street_address = street_address
        self.city = city
        self.state = state
        self.country = country
        self.postal_code = postal_code
        self.set_as_default = set_as_default

    def __call__(self):
        full_name, phone_number = AddressFormValidator(self)()
        data = {
            "full_name": full_name,
            "phone_number": phone_number,
            "street_address": self.street_address,
            "city": self.city,
            "state": self.state,
            "country": self.country,
            "set_as_default": self.set_as_default,
        }
        if self.postal_code:
            data["postal_code"] = self.postal_code
        return data


class AddressFormValidator:
    def __init__(self, v: AddressForm):
        self.v = v
        self.errors: list[str] = []

    def __call__(self):
        full_name = self._full_name_validator(self.v.full_name)
        phone_number = self._phone_number_validator(self.v.phone_number)
        if self.errors:
            raise ValueError(self.errors)
        return full_name, phone_number

    def _phone_number_validator(self, v):
        phone_number_pattern = r"^\+?\d{10,15}$"
        if re.match(phone_number_pattern, self.v):
            return self.v
        self.errors.append("Invalid phone number format")

    def _full_name_validator(self, v):
        full_name_pattern = r"^[A-Za-z\s]{5,100}$"
        if re.match(full_name_pattern, self.v):
            return self.v
        self.errors.append("Invalid full name format")
