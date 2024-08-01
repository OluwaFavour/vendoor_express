from .config import password_context
from .debug import logger


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify the password
    ### Arguments
    - plain_password (str): The plain text password
    - hashed_password (str): The hashed password
    """
    return password_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    """
    Hash the password
    ### Arguments
    - password (str): The plain text password
    """
    return password_context.hash(password)
