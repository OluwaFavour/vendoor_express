import pytest

from .conftest import create_test_user


@pytest.mark.usefixtures("db_session")
def test_read_user(test_client, db_session):
    user, password = create_test_user(db_session, role="admin")
    response = test_client.post(
        "/api/auth/login",
        data={"email": user.email, "password": password},
    )
    response = test_client.get(f"/api/admin/users/{user.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(user.id)
    assert data["email"] == user.email


@pytest.mark.usefixtures("db_session")
def test_read_users(test_client, db_session):
    user, password = create_test_user(db_session, role="admin")
    response = test_client.post(
        "/api/auth/login",
        data={"email": user.email, "password": password},
    )
    response = test_client.get("/api/admin/users/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == str(user.id)
    assert data[0]["email"] == user.email
    assert data[0]["role"] == "admin"
    assert data[0]["is_active"] == True
    assert "hashed_password" not in data[0]
    assert "password" not in data[0]


@pytest.mark.usefixtures("db_session")
def test_make_user_admin(test_client, db_session):
    user, password = create_test_user(db_session, role="admin")
    new_user, _ = create_test_user(db_session, email="john@example.com")
    response = test_client.post(
        "/api/auth/login",
        data={"email": user.email, "password": password},
    )
    response = test_client.put(f"/api/admin/users/{new_user.id}/make-admin")
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "admin"
    assert data["is_active"] == True
    assert "hashed_password" not in data
    assert "password" not in data
