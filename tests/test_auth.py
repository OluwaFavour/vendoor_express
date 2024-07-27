from datetime import timedelta
import pytest
from fastapi import Response
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.main import app
from app.dependencies import get_db
from app.db.models import Base, User
from app.core.security import hash_password, create_token, verify_password
from .conftest import test_client
from app.core.debug import logger
from app.core.config import settings
from app.db.enums import TokenType

# Setup the database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_auth.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create the database tables
Base.metadata.create_all(bind=engine)


# Override the get_db dependency to use the testing database
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session")
def db_session():
    # Create a new database session for each test
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        # Drop tables to reset the database state
        Base.metadata.drop_all(bind=engine)


def create_test_user(db: Session):
    # Get user first
    user = db.execute(
        select(User).filter_by(email="userrt@example.com")
    ).scalar_one_or_none()
    password = "testpassword"

    if user is None:
        hashed_password = hash_password(password)
        user = User(
            full_name="Test User",
            email="userrt@example.com",
            hashed_password=hashed_password,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user, password
    return user, password


def test_login_for_access_token(test_client, db_session):
    user, password = create_test_user(db_session)
    response = test_client.post(
        "/api/auth/login", data={"username": user.email, "password": password}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_for_access_token_invalid_credentials(test_client, db_session):
    response = test_client.post(
        "/api/auth/login",
        data={"username": "invalid@example.com", "password": "invalidpassword"},
    )
    assert response.status_code == 401
    assert response.json() == {
        "detail": "User with email 'invalid@example.com' does not exist."
    }


def test_refresh_access_token(test_client, db_session, mocker):
    user, password = create_test_user(db_session)

    test_client.app_state = {"db": db_session}
    response = test_client.post(
        "/api/auth/login", data={"username": user.email, "password": password}
    )
    refresh_token = test_client.cookies.get("refresh_token")

    response = test_client.post(
        "/api/auth/refresh", headers={"Authorization": f"Bearer {refresh_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data


def test_refresh_access_token_invalid_token(test_client, db_session):
    response = test_client.post(
        "/api/auth/refresh", headers={"Authorization": "Bearer invalidtoken"}
    )
    assert response.status_code == 401
    assert response.json() == {
        "detail": "Could not validate credentials, might be missing, invalid or expired"
    }


def test_refresh_access_token_invalid_token_format(test_client, db_session):
    response = test_client.post(
        "/api/auth/refresh", headers={"Authorization": "invalidtoken"}
    )
    assert response.status_code == 422


def test_logout(test_client, db_session, mocker):
    user, password = create_test_user(db_session)
    mocker.patch("app.core.utils.authenticate", return_value=user)

    response = test_client.post(
        "/api/auth/login", data={"username": user.email, "password": password}
    )
    data = response.json()
    token = data["access_token"]

    response = test_client.post(
        "/api/auth/logout", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json() == {"message": "Successfully logged out"}


def test_logout_all(test_client, db_session, mocker):
    user, password = create_test_user(db_session)
    mocker.patch("app.dependencies.get_current_active_user", return_value=user)

    response = test_client.post(
        "/api/auth/login", data={"username": user.email, "password": password}
    )
    data = response.json()
    token = data["access_token"]

    response = test_client.post(
        "/api/auth/logoutall", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json() == {"message": "Successfully logged out all devices"}


def test_forget_password(test_client, db_session, mocker):
    user, _ = create_test_user(db_session)
    mocker.patch("app.crud.user.get_user_by_email", return_value=user)
    response = test_client.post("/api/auth/forgot-password", json={"email": user.email})
    assert response.status_code == 200
    assert response.json() == {"message": "Password reset link sent to your email"}


def test_reset_password(test_client, db_session, mocker):
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
        json={"new_password": "newpassword"},
    )
    assert response.status_code == 200
    assert response.json() == {"message": "Password reset successful"}
    # Check if the password has been updated
    # user = db_session.execute(select(User).filter_by(email=user.email)).scalar_one()
    # assert verify_password("newpassword", user.hashed_password)


def test_reset_password_invalid_token(test_client, db_session):
    response = test_client.post(
        "/api/auth/reset-password",
        headers={"Authorization": "Bearer invalidtoken"},
        json={"new_password": "newpassword"},
    )
    assert response.status_code == 401
    assert response.json() == {
        "detail": "Could not validate credentials, might be missing, invalid or expired"
    }


def test_reset_password_invalid_token_format(test_client, db_session):
    response = test_client.post(
        "/api/auth/reset-password",
        headers={"Authorization": "invalidtoken"},
        json={"new_password": "newpassword"},
    )
    assert response.status_code == 422
