import pytest

# from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker
# from sqlalchemy.pool import StaticPool

# from app.dependencies import get_db
# from app.db.models import Base
# from app.main import app

# # Setup the database for testing
# SQLALCHEMY_DATABASE_URL = "sqlite://"
# engine = create_engine(
#     SQLALCHEMY_DATABASE_URL,
#     connect_args={"check_same_thread": False},
#     poolclass=StaticPool,
# )
# TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# # Create the database tables
# Base.metadata.create_all(bind=engine)


# # Override the get_db dependency to use the testing database
# def override_get_db():
#     try:
#         db = TestingSessionLocal()
#         yield db
#     finally:
#         db.close()


# app.dependency_overrides[get_db] = override_get_db


# @pytest.fixture(scope="module")
# def db_session():
#     # Create a new database session for each test
#     session = TestingSessionLocal()
#     try:
#         yield session
#     finally:
#         session.close()
#         # Drop tables to reset the database state
#         Base.metadata.drop_all(bind=engine)


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
    assert response.status_code == 400
    assert response.json() == {"detail": "Email already in use"}
