import datetime
import jwt
import pytest
import smtplib
from unittest.mock import Mock

from .conftest import create_test_user, app, get_test_smtp
from app.core.config import settings
from app.core.debug import logger
from app.dependencies import get_smtp
from app.core.security import hash_password


def test_send_verification_email_success(test_client, monkeypatch):
    user_data = {
        "full_name": "Test User",
        "email": "test@example.com",
        "password": "Password@123",
        "role": "user",
    }
    mock_smtp = Mock(spec=smtplib.SMTP)
    monkeypatch.setattr(smtplib, "SMTP", mock_smtp)
    app.dependency_overrides[get_smtp] = get_test_smtp
    response = test_client.post("/api/users/", json=user_data)
    assert response.status_code == 200
    data = response.json()
    assert data == {"message": "Email verification link sent"}
    app.dependency_overrides.pop(get_smtp)


def test_send_verification_email_email_already_in_use(
    test_client, db_session, monkeypatch
):
    user_data = {
        "full_name": "Test User",
        "email": "test@example.com",
        "password": "Password@123",
        "role": "user",
    }
    create_test_user(db_session, email=user_data["email"])
    mock_smtp = Mock(spec=smtplib.SMTP)
    monkeypatch.setattr(smtplib, "SMTP", mock_smtp)
    app.dependency_overrides[get_smtp] = get_test_smtp
    response = test_client.post("/api/users/", json=user_data)
    assert response.status_code == 400
    assert response.json() == {"detail": "Email already in use"}
    app.dependency_overrides.pop(get_smtp)


def test_verify_email_success(test_client):
    user_data = {
        "full_name": "Test User",
        "email": "test@example.com",
        "password": "Password@123",
        "role": "user",
    }
    salt = hash_password(user_data["password"])
    expire = datetime.datetime.now(datetime.UTC) + datetime.timedelta(
        minutes=settings.reset_token_expire_minutes
    )
    email = user_data["email"]
    full_name = user_data["full_name"]
    data = {
        "sub": f"{email}:{salt}:user:{full_name}",
        "exp": expire,
    }
    to_encode = data.copy()
    token = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    response = test_client.get(f"/api/users/verify-email?token={token}")
    assert response.url == f"{settings.frontend_url}/email/verify"


@pytest.mark.usefixtures("db_session")
def test_read_users_me(test_client, db_session):
    user, password = create_test_user(db_session)
    response = test_client.post(
        "/api/auth/login",
        data={"email": user.email, "password": password},
    )
    response = test_client.get("/api/users/me")
    logger.debug(f"Response: {response.json()}")
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == user.email
