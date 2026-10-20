
def test_register_user_returns_created_response(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "arslan@example.com",
            "password": "StrongPassword123!",
            "display_name": "Test User",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "arslan@example.com"
    assert data["display_name"] == "Test User"
    assert "id" in data
    assert "password" not in data
    assert "password_hash" not in data


def test_register_user_rejects_duplicate_email(client):
    payload = {
        "email": "duplicate@example.com",
        "password": "StrongPassword123!",
        "display_name": "Test User",
    }

    first_response = client.post("/api/v1/auth/register", json=payload)
    second_response = client.post("/api/v1/auth/register", json=payload)

    assert first_response.status_code == 201
    assert second_response.status_code == 409


def test_register_user_rejects_invalid_email(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "not-an-email",
            "password": "StrongPassword123!",
            "display_name": "Test User",
        },
    )

    assert response.status_code == 422


def test_register_user_rejects_short_password(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "shortpass@example.com",
            "password": "123",
            "display_name": "Test User",
        },
    )

    assert response.status_code == 422


from app.models.models import User, UserStatus
from app.core.security import hash_password


def test_login_returns_access_token(client):
    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "login@example.com",
            "password": "StrongPassword123!",
            "display_name": "Login User",
        },
    )
    assert register_response.status_code == 201

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "login@example.com",
            "password": "StrongPassword123!",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert isinstance(data["access_token"], str)
    assert len(data["access_token"]) > 0


def test_login_rejects_wrong_password(client):
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "wrongpass@example.com",
            "password": "StrongPassword123!",
            "display_name": "Login User",
        },
    )

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "wrongpass@example.com",
            "password": "WrongPassword123!",
        },
    )

    assert response.status_code == 401


def test_login_rejects_unknown_email(client):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "unknown@example.com",
            "password": "StrongPassword123!",
        },
    )

    assert response.status_code == 401


def test_login_rejects_suspended_user(client, db_session):
    user = User(
        email="suspended@example.com",
        email_normalized="suspended@example.com",
        password_hash=hash_password("StrongPassword123!"),
        display_name="Suspended User",
        status=UserStatus.SUSPENDED,
    )
    db_session.add(user)
    db_session.flush()

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "suspended@example.com",
            "password": "StrongPassword123!",
        },
    )

    assert response.status_code == 401



def test_me_returns_current_user_profile(client):
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "profile@example.com",
            "password": "StrongPassword123!",
            "display_name": "Profile User",
        },
    )

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "profile@example.com",
            "password": "StrongPassword123!",
        },
    )
    assert login_response.status_code == 200

    token = login_response.json()["access_token"]
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["email"] == "profile@example.com"
    assert response.json()["display_name"] == "Profile User"
    assert "password_hash" not in response.json()


def test_me_rejects_missing_token(client):
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401


def test_me_rejects_invalid_token(client):
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid.token.value"},
    )

    assert response.status_code == 401

