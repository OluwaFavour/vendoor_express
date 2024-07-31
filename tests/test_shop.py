import pytest

from .conftest import create_test_user
from app.core.debug import logger
from app.core import utils


def test_create_vendor_profile(test_client, db_session, monkeypatch):
    data = {
        "user_phone_number": "1234567890",
        "proof_of_identity_type": "national_id",
        "name": "test",
        "description": "test",
        "email": "shop@example.com",
        "phone_number": "1234567890",
        "type": "products",
        "category": "test",
        "wanted_help": "sell_online",
    }
    user, password = create_test_user(db_session)
    response = test_client.post(
        "/api/auth/login", data={"email": user.email, "password": password}
    )
    logger.info(response.json())
    session_id = response.cookies["session_id"]
    test_client.cookies.update({"session_id": session_id})
    monkeypatch.setattr(
        utils, "upload_image", lambda x: "https://example.com/image.jpg"
    )
    response = test_client.post(
        "/api/shop/",
        data=data,
        files={
            "logo": open("tests/images/logo.png", "rb"),
            "proof_of_identity_image": open("tests/images/logo.png", "rb"),
            "business_registration_certificate_image": open(
                "tests/images/logo.png", "rb"
            ),
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "test"
    assert data["description"] == "test"
    assert data["email"] == "shop@example.com"


def test_read_me(test_client, db_session, monkeypatch):
    data = {
        "user_phone_number": "1234567890",
        "proof_of_identity_type": "national_id",
        "name": "test",
        "description": "test",
        "email": "shop@example.com",
        "phone_number": "1234567890",
        "type": "products",
        "category": "test",
        "wanted_help": "sell_online",
    }
    user, password = create_test_user(db_session)
    response = test_client.post(
        "/api/auth/login", data={"email": user.email, "password": password}
    )
    logger.info(response.json())
    session_id = response.cookies["session_id"]
    test_client.cookies.update({"session_id": session_id})
    monkeypatch.setattr(utils, "upload_image", lambda: "https://example.com/image.jpg")
    response = test_client.post(
        "/api/shop/",
        data=data,
        files={
            "logo": open("tests/images/logo.png", "rb"),
            "proof_of_identity_image": open("tests/images/logo.png", "rb"),
            "business_registration_certificate_image": open(
                "tests/images/logo.png", "rb"
            ),
        },
    )
    response = test_client.get("/api/shop/me")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "test"
