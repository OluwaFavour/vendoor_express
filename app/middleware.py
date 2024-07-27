import jwt
from typing import Callable

from fastapi import Request, HTTPException, status
from .core.debug import logger
from .core.security import refresh_access_token, validate_token
from .db.enums import TokenType
from .dependencies import get_db


async def auto_refresh_token_middleware(request: Request, call_next: Callable):
    token = request.headers.get("Authorization")
    if token:
        token = token.split(" ")[1]  # Remove the Bearer prefix
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials, might be missing, invalid or expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
        db = next(get_db())
        try:
            user = validate_token(
                token=token, token_type=TokenType.ACCESS.value, db=db
            )  # Validates the token and returns a boolean value False if the token is invalid or a user object if the token is valid
        except jwt.PyJWTError or HTTPException:
            refresh_token = request.cookies.get("refresh_token")
            if refresh_token:
                try:
                    access_token = refresh_access_token(
                        refresh_token=refresh_token, db=db
                    )
                except jwt.PyJWTError:
                    raise credentials_exception
                # Modify the request headers to include the new access token
                response = await call_next(request)
                response.headers["Authorization"] = f"Bearer {access_token}"
                return response
            raise credentials_exception
    return await call_next(request)
