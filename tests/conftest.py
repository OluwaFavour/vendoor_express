import pytest
import smtplib
from typing import Optional

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.db.models import User
from app.core.config import settings
from app.dependencies import get_db
from app.db.models import Base
from app.main import app

# Setup the database for testing
SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create the database tables
Base.metadata.create_all(bind=engine)


@pytest.fixture(scope="function")
def db_session():
    try:
        connection = engine.connect()
        transaction = connection.begin()
        session = TestingSessionLocal(bind=connection)

        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture(scope="function")
def test_client():
    client = TestClient(app)
    yield client
    client.close()


# # Override the get_db dependency to use the testing database
def override_get_db():
    try:
        connection = engine.connect()
        transaction = connection.begin()
        session = TestingSessionLocal(bind=connection)

        yield session
    finally:
        session.close()


app.dependency_overrides[get_db] = override_get_db


def create_test_user(
    db: Session, role: str = "user", email: str = "userrt@example.com"
) -> tuple[User, str]:
    from app.core.security import hash_password

    password = "testpassword"
    hashed_password = hash_password(password)
    user = User(
        full_name="Test User",
        email=email,
        hashed_password=hashed_password,
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user, password


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
