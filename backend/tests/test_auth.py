"""Tests de l'authentification JWT et du RBAC."""
from fastapi.testclient import TestClient

from app.models.user import UserRole


def test_login_success(client: TestClient, make_user) -> None:
    user, _ = make_user(UserRole.USER, email="login@example.com")
    response = client.post("/api/auth/login", json={"email": user.email, "password": "test-password"})
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["email"] == user.email
    assert body["user"]["role"] == "USER"


def test_login_wrong_password(client: TestClient, make_user) -> None:
    user, _ = make_user(UserRole.USER, email="wrong@example.com")
    response = client.post("/api/auth/login", json={"email": user.email, "password": "wrong"})
    assert response.status_code == 401
    # Message générique : ne révèle pas si l'email existe.
    assert response.json()["detail"] == "Invalid email or password"


def test_login_unknown_email(client: TestClient) -> None:
    response = client.post("/api/auth/login", json={"email": "ghost@example.com", "password": "x"})
    assert response.status_code == 401


def test_me_requires_token(client: TestClient) -> None:
    assert client.get("/api/auth/me").status_code == 401


def test_me_with_token(client: TestClient, make_user) -> None:
    _, headers = make_user(UserRole.ADMIN, email="me@example.com")
    response = client.get("/api/auth/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["role"] == "ADMIN"


def test_expired_or_invalid_token_rejected(client: TestClient) -> None:
    response = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert response.status_code == 401