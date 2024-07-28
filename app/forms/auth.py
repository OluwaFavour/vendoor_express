from typing import Annotated

from fastapi import Form
from pydantic import EmailStr


class LoginForm:
    def __init__(
        self,
        email: Annotated[
            EmailStr, Form(title="Email", description="Email of the user")
        ],
        password: Annotated[
            str,
            Form(
                title="Password",
                description="Password of the user",
            ),
        ],
    ):
        self.email = email
        self.password = password
