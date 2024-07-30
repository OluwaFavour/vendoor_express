import pytest

from .conftest import create_test_user
from app.core.debug import logger


def test_create_user_success(test_client):
    user_data = {
        "full_name": "Test User",
        "email": "test@example.com",
        "password": "Password@123",
        "role": "user",
    }
    response = test_client.post("/api/users/", json=user_data)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == user_data["email"]
    assert data["full_name"] == user_data["full_name"]
    assert "id" in data


def test_create_user_email_already_in_use(test_client):
    user_data = {
        "full_name": "Test User",
        "email": "test@example.com",
        "password": "Password@123",
        "role": "user",
    }
    response = test_client.post("/api/users/", json=user_data)
    response = test_client.post("/api/users/", json=user_data)
    assert response.status_code == 400
    assert response.json() == {"detail": "Email already in use"}


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
