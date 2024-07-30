from datetime import timedelta
import pytest
import smtplib
from unittest.mock import Mock

from sqlalchemy.future import select

from app.dependencies import get_smtp
from app.db.models import User
from app.core.security import create_token, verify_password
from app.core.debug import logger
from app.core.config import settings
from app.crud import user as user_crud
from app.db.enums import TokenType

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


@pytest.mark.usefixtures("db_session")
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


@pytest.mark.usefixtures("db_session")
def test_logout(test_client, db_session, mocker):
    user, password = create_test_user(db_session)

    response = test_client.post(
        "/api/auth/login", data={"email": user.email, "password": password}
    )

    response = test_client.post("/api/auth/logout")
    assert response.status_code == 200
    assert response.json() == {"message": "Successfully logged out"}


@pytest.mark.usefixtures("db_session")
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


@pytest.mark.usefixtures("db_session")
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


@pytest.mark.usefixtures("db_session")
def test_reset_password(test_client, db_session):
    user, _ = create_test_user(db_session)
    reset_token = create_token(
        data={"sub": str(user.id)},
        db=db_session,
        expires_delta=timedelta(minutes=settings.reset_token_expire_minutes),
        token_type=TokenType.RESET.value,
    )
    response = test_client.post(
        "/api/auth/reset-password",
        headers={"Authorization": f"Bearer {reset_token}"},
        json={"new_password": "newpasswordA1$"},
    )
    assert response.status_code == 200
    assert response.json() == {"message": "Password reset successful"}
    # Check if the password has been updated
    user = db_session.execute(select(User).filter_by(email=user.email)).scalar_one()
    assert verify_password("newpasswordA1$", user.hashed_password)


def test_reset_password_invalid_token(test_client):
    response = test_client.post(
        "/api/auth/reset-password",
        headers={"Authorization": "Bearer invalidtoken"},
        json={"new_password": "newpasswordA1$"},
    )
    assert response.status_code == 401
    assert response.json() == {
        "detail": "Could not validate credentials, might be missing, invalid or expired"
    }


def test_reset_password_invalid_token_format(test_client):
    response = test_client.post(
        "/api/auth/reset-password",
        headers={"Authorization": "invalidtoken"},
        json={"new_password": "newpasswordA1$"},
    )
    assert response.status_code == 422
