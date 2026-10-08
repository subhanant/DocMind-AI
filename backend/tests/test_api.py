"""
Backend tests for DocuMind AI.

Tests use an in-memory SQLite database via async SQLAlchemy
so no external PostgreSQL is needed for unit tests.
"""
import asyncio
import io
import uuid
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.database import Base, get_db
from app.main import app

# Use SQLite for testing (in-memory)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    async_session = async_sessionmaker(test_engine, expire_on_commit=False)
    async with async_session() as session:
        yield session
        for table in reversed(Base.metadata.sorted_tables):
            await session.execute(table.delete())
        await session.commit()


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c

    app.dependency_overrides.clear()


# ─── Helper fixtures ──────────────────────────────────────────────────────────

TEST_USER = {
    "email": "test@documind.ai",
    "password": "TestPass123",
    "full_name": "Test User",
}


async def register_and_login(client: AsyncClient) -> dict:
    """Register a user and return auth headers."""
    await client.post("/api/auth/register", json=TEST_USER)
    login_resp = await client.post(
        "/api/auth/login",
        json={"email": TEST_USER["email"], "password": TEST_USER["password"]},
    )
    data = login_resp.json()
    token = data["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ─── Health Tests ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    response = await client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "status" in body["data"]


# ─── Auth Tests ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    response = await client.post("/api/auth/register", json=TEST_USER)
    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert "access_token" in body["data"]
    assert body["data"]["user"]["email"] == TEST_USER["email"]


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    await client.post("/api/auth/register", json=TEST_USER)
    response = await client.post("/api/auth/register", json=TEST_USER)
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_register_weak_password(client: AsyncClient):
    user = {**TEST_USER, "email": "weak@test.com", "password": "short"}
    response = await client.post("/api/auth/register", json=user)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    await client.post("/api/auth/register", json=TEST_USER)
    response = await client.post(
        "/api/auth/login",
        json={"email": TEST_USER["email"], "password": TEST_USER["password"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "access_token" in body["data"]


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await client.post("/api/auth/register", json=TEST_USER)
    response = await client.post(
        "/api/auth/login",
        json={"email": TEST_USER["email"], "password": "WrongPass123"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    response = await client.post(
        "/api/auth/login",
        json={"email": "nobody@test.com", "password": "TestPass123"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_authenticated(client: AsyncClient):
    headers = await register_and_login(client)
    response = await client.get("/api/auth/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["data"]["email"] == TEST_USER["email"]


@pytest.mark.asyncio
async def test_get_me_unauthenticated(client: AsyncClient):
    response = await client.get("/api/auth/me")
    assert response.status_code == 401


# ─── Document Upload Tests ────────────────────────────────────────────────────

def make_pdf_file(name: str = "test.pdf", size: int = 1024) -> tuple:
    """Create a minimal fake PDF file for testing."""
    content = b"%PDF-1.4\n" + b"x" * (size - 9)
    return (name, io.BytesIO(content), "application/pdf")


@pytest.mark.asyncio
async def test_upload_document_success(client: AsyncClient):
    headers = await register_and_login(client)
    name, data, mime = make_pdf_file()
    response = await client.post(
        "/api/documents/upload",
        files={"files": (name, data, mime)},
        headers=headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert body["data"]["document"]["original_filename"] == name


@pytest.mark.asyncio
async def test_upload_invalid_file_type(client: AsyncClient):
    headers = await register_and_login(client)
    response = await client.post(
        "/api/documents/upload",
        files={"files": ("virus.exe", io.BytesIO(b"MZ\x90"), "application/octet-stream")},
        headers=headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_upload_requires_auth(client: AsyncClient):
    name, data, mime = make_pdf_file()
    response = await client.post(
        "/api/documents/upload",
        files={"files": (name, data, mime)},
    )
    assert response.status_code == 401


# ─── Document Listing Tests ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_documents_empty(client: AsyncClient):
    headers = await register_and_login(client)
    response = await client.get("/api/documents", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["total"] == 0
    assert body["data"]["items"] == []


@pytest.mark.asyncio
async def test_list_documents_after_upload(client: AsyncClient):
    headers = await register_and_login(client)
    name, data, mime = make_pdf_file("invoice.pdf")
    await client.post(
        "/api/documents/upload",
        files={"files": (name, data, mime)},
        headers=headers,
    )
    response = await client.get("/api/documents", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["total"] == 1
    assert body["data"]["items"][0]["original_filename"] == "invoice.pdf"


# ─── Document Deletion Tests ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_document(client: AsyncClient):
    headers = await register_and_login(client)
    name, data, mime = make_pdf_file("to_delete.pdf")
    upload_resp = await client.post(
        "/api/documents/upload",
        files={"files": (name, data, mime)},
        headers=headers,
    )
    doc_id = upload_resp.json()["data"]["document"]["id"]

    delete_resp = await client.delete(f"/api/documents/{doc_id}", headers=headers)
    assert delete_resp.status_code == 200
    assert delete_resp.json()["success"] is True

    # Verify gone
    get_resp = await client.get(f"/api/documents/{doc_id}", headers=headers)
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_other_users_document(client: AsyncClient):
    """Users cannot delete documents that belong to other users."""
    headers1 = await register_and_login(client)

    # Register second user
    user2 = {**TEST_USER, "email": "user2@test.com"}
    await client.post("/api/auth/register", json=user2)
    login2 = await client.post("/api/auth/login", json={"email": user2["email"], "password": user2["password"]})
    headers2 = {"Authorization": f"Bearer {login2.json()['data']['access_token']}"}

    # User 1 uploads
    name, data, mime = make_pdf_file("private.pdf")
    upload_resp = await client.post(
        "/api/documents/upload",
        files={"files": (name, data, mime)},
        headers=headers1,
    )
    doc_id = upload_resp.json()["data"]["document"]["id"]

    # User 2 tries to delete User 1's document
    delete_resp = await client.delete(f"/api/documents/{doc_id}", headers=headers2)
    assert delete_resp.status_code == 404


# ─── Notification Tests ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_notifications_created_on_upload(client: AsyncClient):
    headers = await register_and_login(client)
    name, data, mime = make_pdf_file("notify_test.pdf")
    await client.post(
        "/api/documents/upload",
        files={"files": (name, data, mime)},
        headers=headers,
    )
    notif_resp = await client.get("/api/notifications", headers=headers)
    assert notif_resp.status_code == 200
    body = notif_resp.json()
    assert body["data"]["total"] >= 1
    assert body["data"]["unread_count"] >= 1


@pytest.mark.asyncio
async def test_mark_notification_read(client: AsyncClient):
    headers = await register_and_login(client)
    name, data, mime = make_pdf_file("mark_read.pdf")
    await client.post(
        "/api/documents/upload",
        files={"files": (name, data, mime)},
        headers=headers,
    )
    notifs = await client.get("/api/notifications", headers=headers)
    notif_id = notifs.json()["data"]["items"][0]["id"]

    patch_resp = await client.patch(f"/api/notifications/{notif_id}/read", headers=headers)
    assert patch_resp.status_code == 200
    assert patch_resp.json()["data"]["is_read"] is True


@pytest.mark.asyncio
async def test_mark_all_notifications_read(client: AsyncClient):
    headers = await register_and_login(client)
    for i in range(3):
        name, data, mime = make_pdf_file(f"bulk_{i}.pdf")
        await client.post(
            "/api/documents/upload",
            files={"files": (name, data, mime)},
            headers=headers,
        )

    patch_resp = await client.patch("/api/notifications/read-all", headers=headers)
    assert patch_resp.status_code == 200

    notifs = await client.get("/api/notifications", headers=headers)
    assert notifs.json()["data"]["unread_count"] == 0


@pytest.mark.asyncio
async def test_notifications_are_paginated_and_filterable(client: AsyncClient):
    headers = await register_and_login(client)
    for i in range(3):
        name, data, mime = make_pdf_file(f"paged_{i}.pdf")
        await client.post(
            "/api/documents/upload",
            files={"files": (name, data, mime)},
            headers=headers,
        )

    page_one = await client.get("/api/notifications?page=1&size=2", headers=headers)
    body = page_one.json()["data"]
    assert body["total"] == 3
    assert body["page"] == 1
    assert body["size"] == 2
    assert body["pages"] == 2
    assert len(body["items"]) == 2

    first_notification_id = body["items"][0]["id"]
    await client.patch(f"/api/notifications/{first_notification_id}/read", headers=headers)

    unread = await client.get("/api/notifications?unread_only=true&size=10", headers=headers)
    unread_body = unread.json()["data"]
    assert unread_body["total"] == 2
    assert unread_body["unread_count"] == 2
    assert all(not item["is_read"] for item in unread_body["items"])
