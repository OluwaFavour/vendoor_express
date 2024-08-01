from datetime import timedelta, datetime, UTC
import jwt
import smtplib
from unittest.mock import Mock

from sqlalchemy.future import select

from app.dependencies import get_smtp
from app.db.models import User
from app.core.security import verify_password
from app.core.debug import logger
from app.core.config import settings
from app.crud import user as user_crud

from .conftest import app, create_test_user


# SMTP connection for testing
def get_test_smtp():
    """Manage the SMTP connection by creating a new connection for each request"""
    smtp = smtplib.SMTP(settings.smtp_host, settings.smtp_port)
    try:
        smtp.starttls()
        smtp.login(settings.smtp_login, settings.smtp_password)
        yield smtp
    finally:
        smtp.quit()


def test_login(test_client, db_session):
    user, password = create_test_user(db_session)
    logger.debug(f"User: {user}")
    response = test_client.post(
        "/api/auth/login", data={"email": user.email, "password": password}
    )
    assert response.status_code == 200
    assert "session_id" in response.cookies
    data = response.json()
    assert data["message"] == "Successfully logged in"


def test_login_invalid_credentials(test_client):
    response = test_client.post(
        "/api/auth/login",
        data={"email": "invalid@example.com", "password": "invalidpassword"},
    )
    assert response.status_code == 401
    assert response.json() == {
        "detail": "User with email 'invalid@example.com' does not exist."
    }


def test_logout(test_client, db_session):
    user, password = create_test_user(db_session)

    response = test_client.post(
        "/api/auth/login", data={"email": user.email, "password": password}
    )

    response = test_client.post("/api/auth/logout")
    assert response.status_code == 200
    assert response.json() == {"message": "Successfully logged out"}


def test_logout_all(test_client, db_session):
    user, password = create_test_user(db_session)
    response = test_client.post(
        "/api/auth/login", data={"email": user.email, "password": password}
    )
    logger.debug(f"Response: {response.json()}")
    response = test_client.post("/api/auth/logoutall")
    assert response.status_code == 200
    assert response.json() == {
        "message": "Successfully logged out all devices, or rather, all sessions"
    }


def test_forget_password(test_client, db_session, monkeypatch):
    mock_smtp = Mock(spec=smtplib.SMTP)
    monkeypatch.setattr(smtplib, "SMTP", mock_smtp)
    app.dependency_overrides[get_smtp] = get_test_smtp

    user, _ = create_test_user(db_session)
    monkeypatch.setattr(user_crud, "get_user_by_email", user)
    response = test_client.post("/api/auth/forgot-password", json={"email": user.email})
    assert response.status_code == 200
    assert response.json() == {"message": "Password reset link sent to your email"}
    app.dependency_overrides.pop(get_smtp)


def test_reset_password(test_client, db_session):
    user, _ = create_test_user(db_session)
    expire = datetime.now(UTC) + timedelta(minutes=settings.reset_token_expire_minutes)
    data = {"sub": str(user.id), "exp": expire}
    to_encode = data.copy()
    reset_token = jwt.encode(
        to_encode, settings.secret_key, algorithm=settings.algorithm
    )
    response = test_client.post(
        "/api/auth/reset-password",
        headers={"Authorization": f"Bearer {reset_token}"},
        json={"new_password": "newpasswordA1$"},
    )
    assert response.status_code == 200
    assert response.json() == {"message": "Password reset successful"}


def test_reset_password_invalid_token(test_client):
    response = test_client.post(
        "/api/auth/reset-password",
        headers={"Authorization": "Bearer invalidtoken"},
        json={"new_password": "newpasswordA1$"},
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Could not validate credentials"}


def test_reset_password_invalid_token_format(test_client):
    response = test_client.post(
        "/api/auth/reset-password",
        headers={"Authorization": "invalidtoken"},
        json={"new_password": "newpasswordA1$"},
    )
    assert response.status_code == 422
