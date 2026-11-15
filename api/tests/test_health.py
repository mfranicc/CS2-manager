from httpx import ASGITransport, AsyncClient

from app.core.deps import get_db
from app.main import create_app


async def test_health_returns_ok(client):
    resp = await client.get("/health/")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_unknown_route_uses_error_format(client):
    resp = await client.get("/nepostojeca-ruta")
    assert resp.status_code == 404
    assert resp.json() == {"code": "not_found", "message": "Not Found"}


async def test_wrong_method_uses_error_format(client):
    resp = await client.post("/health/")
    assert resp.status_code == 405
    assert resp.json()["code"] == "method_not_allowed"


async def _broken_db():
    raise RuntimeError("baza nije dostupna")
    yield


async def test_unexpected_error_uses_error_format():
    app = create_app()
    # Simulira pad baze: svaka ruta koja trazi sesiju dobiva iznimku
    app.dependency_overrides[get_db] = _broken_db
    # raise_app_exceptions=False: klijent vraca odgovor kao pravi preglednik,
    # umjesto da iznimku proslijedi u test
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/health/")
    assert resp.status_code == 500
    assert resp.json() == {
        "code": "internal_error",
        "message": "Dogodila se neocekivana pogreska",
    }
    # Detalji iznimke ne smiju procuriti klijentu
    assert "baza" not in resp.text
