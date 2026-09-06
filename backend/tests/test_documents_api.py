"""Tests API des documents : upload, liste, détail, suppression, RBAC."""
from fastapi.testclient import TestClient

from app.models.user import UserRole
from tests.helpers import make_pdf_bytes, make_png_bytes


def _upload(client: TestClient, headers: dict, filename: str = "note.png", data: bytes | None = None):
    return client.post(
        "/api/documents/upload",
        headers=headers,
        files={"file": (filename, data or make_png_bytes(), "image/png")},
    )


def test_upload_requires_auth(client: TestClient) -> None:
    assert client.post("/api/documents/upload", files={"file": ("a.png", b"x", "image/png")}).status_code == 401


def test_upload_png(client: TestClient, make_user) -> None:
    _, headers = make_user()
    response = _upload(client, headers)
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "UPLOADED"
    assert body["content_type"] == "image/png"
    assert body["file_size_bytes"] > 0


def test_upload_pdf(client: TestClient, make_user) -> None:
    _, headers = make_user()
    response = _upload(client, headers, filename="doc.pdf", data=make_pdf_bytes())
    assert response.status_code == 201
    assert response.json()["content_type"] == "application/pdf"


def test_upload_forged_extension_rejected(client: TestClient, make_user) -> None:
    _, headers = make_user()
    response = _upload(client, headers, filename="fake.png", data=make_pdf_bytes())
    assert response.status_code == 400


def test_upload_oversized_rejected(client: TestClient, make_user, monkeypatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "max_upload_size_mb", 0)
    _, headers = make_user()
    response = _upload(client, headers)
    assert response.status_code == 400


def test_list_and_detail(client: TestClient, make_user) -> None:
    _, headers = make_user()
    upload = _upload(client, headers)
    document_id = upload.json()["id"]

    listing = client.get("/api/documents", headers=headers)
    assert listing.status_code == 200
    assert listing.json()["total"] == 1

    detail = client.get(f"/api/documents/{document_id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["id"] == document_id
    assert detail.json()["analysis"] is None


def test_user_only_sees_own_documents(client: TestClient, make_user) -> None:
    user_a, headers_a = make_user(email="a@example.com")
    _, headers_b = make_user(email="b@example.com")
    _upload(client, headers_a)

    listing_b = client.get("/api/documents", headers=headers_b)
    assert listing_b.json()["total"] == 0

    # Détail d'un document d'un autre utilisateur : 404 (pas de fuite d'existence).
    doc_id = client.get("/api/documents", headers=headers_a).json()["items"][0]["id"]
    assert client.get(f"/api/documents/{doc_id}", headers=headers_b).status_code == 404


def test_delete_own_document(client: TestClient, make_user) -> None:
    _, headers = make_user()
    doc_id = _upload(client, headers).json()["id"]
    response = client.delete(f"/api/documents/{doc_id}", headers=headers)
    assert response.status_code == 204
    assert client.get(f"/api/documents/{doc_id}", headers=headers).status_code == 404


def test_user_cannot_delete_other_document(client: TestClient, make_user) -> None:
    _, headers_a = make_user(email="owner@example.com")
    _, headers_b = make_user(email="intruder@example.com")
    doc_id = _upload(client, headers_a).json()["id"]
    # 404 : l'existence du document d'autrui n'est pas révélée.
    assert client.delete(f"/api/documents/{doc_id}", headers=headers_b).status_code == 404