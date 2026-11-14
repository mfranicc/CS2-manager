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
