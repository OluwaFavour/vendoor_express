import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.dependencies import get_db
from app.db.models import Base, User
from app.core.utils import hash_password
from .conftest import test_client
from app.core.debug import logger

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


@pytest.fixture(scope="package")
def db_session():
    # Create a new database session for each test
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        # Drop tables to reset the database state


def create_test_user(db):
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
    db_data = db_session.execute(select(User)).scalar_one_or_none()
    logger.info(db_data)
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
