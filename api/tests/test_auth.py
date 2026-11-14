from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import settings
from tests.conftest import auth_header


async def login(client, username, password):
    return await client.post(
        "/auth/login", json={"username": username, "password": password}
    )


# --- prijava -------------------------------------------------------------------


async def test_login_success_returns_both_tokens(client, admin_user):
    resp = await login(client, "testadmin", "admin123")
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"] and body["refresh_token"]


async def test_login_wrong_password(client, admin_user):
    resp = await login(client, "testadmin", "kriva")
    assert resp.status_code == 401
    assert resp.json()["code"] == "invalid_credentials"


async def test_login_unknown_user_same_response_as_wrong_password(client, admin_user):
    wrong_password = await login(client, "testadmin", "kriva")
    unknown_user = await login(client, "nepostojeci", "kriva")
    assert unknown_user.status_code == 401
    # Odgovor ne smije odati postoji li korisnicko ime
    assert unknown_user.json() == wrong_password.json()


async def test_login_missing_password_is_validation_error(client):
    resp = await client.post("/auth/login", json={"username": "testadmin"})
    assert resp.status_code == 422
    assert resp.json()["code"] == "validation_error"
    assert resp.json()["errors"][0]["field"] == "password"


async def test_login_password_over_72_bytes_rejected(client, admin_user):
    resp = await login(client, "testadmin", "č" * 40)  # 40 znakova, 80 bajtova
    assert resp.status_code == 422


# --- token pri svakom zahtjevu ---------------------------------------------------


async def test_me_returns_current_user_without_password_hash(client, manager_user):
    headers = await auth_header(client, "testmanager", "manager123")
    resp = await client.get("/auth/me", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["username"] == "testmanager"
    assert body["role"] == "manager"
    assert "password_hash" not in body


async def test_me_without_token(client):
    resp = await client.get("/auth/me")
    assert resp.status_code == 401
    assert resp.json()["code"] == "invalid_credentials"


async def test_me_with_tampered_token(client, admin_user):
    headers = await auth_header(client, "testadmin", "admin123")
    token = headers["Authorization"].removeprefix("Bearer ")
    resp = await client.get(
        "/auth/me", headers={"Authorization": f"Bearer {token[:-4]}abcd"}
    )
    assert resp.status_code == 401


async def test_me_with_token_signed_by_other_key(client, admin_user):
    token = jwt.encode(
        {
            "sub": str(admin_user.id),
            "role": "admin",
            "type": "access",
            "iss": settings.jwt_issuer,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        "neki-drugi-kljuc-koji-posluzitelj-ne-poznaje",
        algorithm="HS256",
    )
    resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


async def test_me_with_expired_token(client, admin_user):
    token = jwt.encode(
        {
            "sub": str(admin_user.id),
            "role": "admin",
            "type": "access",
            "iss": settings.jwt_issuer,
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
        },
        settings.secret_key,
        algorithm="HS256",
    )
    resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
    assert resp.json()["code"] == "token_expired"


async def test_me_rejects_refresh_token(client, admin_user):
    tokens = (await login(client, "testadmin", "admin123")).json()
    resp = await client.get(
        "/auth/me", headers={"Authorization": f"Bearer {tokens['refresh_token']}"}
    )
    assert resp.status_code == 401


# --- obnova tokena ---------------------------------------------------------------


async def test_refresh_returns_new_working_pair(client, admin_user):
    tokens = (await login(client, "testadmin", "admin123")).json()
    resp = await client.post(
        "/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert resp.status_code == 200
    new_access = resp.json()["access_token"]
    me = await client.get("/auth/me", headers={"Authorization": f"Bearer {new_access}"})
    assert me.status_code == 200


async def test_refresh_rejects_access_token(client, admin_user):
    tokens = (await login(client, "testadmin", "admin123")).json()
    resp = await client.post(
        "/auth/refresh", json={"refresh_token": tokens["access_token"]}
    )
    assert resp.status_code == 401
    assert resp.json()["code"] == "invalid_credentials"


async def test_refresh_rejects_garbage(client):
    resp = await client.post("/auth/refresh", json={"refresh_token": "nije.jwt.token"})
    assert resp.status_code == 401


# --- uloge ---------------------------------------------------------------------


async def test_manager_cannot_create_tournament(client, manager_user):
    headers = await auth_header(client, "testmanager", "manager123")
    resp = await client.post(
        "/tournaments/",
        json={
            "name": "Hak",
            "max_teams": 8,
            "registration_deadline": "2030-01-01T12:00:00+01:00",
        },
        headers=headers,
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "forbidden"


async def test_admin_cannot_create_team(client, admin_user):
    headers = await auth_header(client, "testadmin", "admin123")
    resp = await client.post(
        "/teams/", json={"name": "Admin Tim", "tag": "ADM"}, headers=headers
    )
    assert resp.status_code == 403
