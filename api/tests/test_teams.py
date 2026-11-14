from app.models import Registration
from tests.conftest import auth_header, create_team

# --- popis i stranicenje ---------------------------------------------------------


async def test_manager_lists_only_own_teams(client, team, rival_team):
    headers = await auth_header(client, "testmanager", "manager123")
    resp = await client.get("/teams/", headers=headers)
    assert resp.status_code == 200
    assert [t["name"] for t in resp.json()] == ["Alpha"]


async def test_admin_lists_all_teams(client, admin_user, team, rival_team):
    headers = await auth_header(client, "testadmin", "admin123")
    resp = await client.get("/teams/", headers=headers)
    assert [t["name"] for t in resp.json()] == ["Alpha", "Bravo"]


async def test_list_pagination(client, db, manager_user):
    for name in ["T1", "T2", "T3", "T4"]:
        await create_team(db, manager_user, name, players=0)
    headers = await auth_header(client, "testmanager", "manager123")
    resp = await client.get("/teams/?limit=2&offset=1", headers=headers)
    assert [t["name"] for t in resp.json()] == ["T2", "T3"]


async def test_list_limit_out_of_range(client, manager_user):
    headers = await auth_header(client, "testmanager", "manager123")
    resp = await client.get("/teams/?limit=0", headers=headers)
    assert resp.status_code == 422


# --- vlasnistvo ------------------------------------------------------------------


async def test_manager_cannot_read_other_team(client, team, rival_team):
    headers = await auth_header(client, "testmanager", "manager123")
    resp = await client.get(f"/teams/{rival_team.id}", headers=headers)
    assert resp.status_code == 403
    assert resp.json()["code"] == "forbidden"


async def test_manager_cannot_update_other_team(client, team, rival_team):
    headers = await auth_header(client, "testmanager", "manager123")
    resp = await client.patch(
        f"/teams/{rival_team.id}", json={"tag": "HAX"}, headers=headers
    )
    assert resp.status_code == 403


async def test_manager_cannot_delete_other_team(client, team, rival_team):
    headers = await auth_header(client, "testmanager", "manager123")
    resp = await client.delete(f"/teams/{rival_team.id}", headers=headers)
    assert resp.status_code == 403


async def test_admin_reads_any_team(client, admin_user, rival_team):
    headers = await auth_header(client, "testadmin", "admin123")
    resp = await client.get(f"/teams/{rival_team.id}", headers=headers)
    assert resp.status_code == 200


async def test_unknown_team_is_404(client, manager_user):
    headers = await auth_header(client, "testmanager", "manager123")
    resp = await client.get("/teams/999", headers=headers)
    assert resp.status_code == 404


# --- stvaranje i izmjena -----------------------------------------------------------


async def test_create_team_sets_owner_from_token(client, manager_user):
    headers = await auth_header(client, "testmanager", "manager123")
    resp = await client.post(
        "/teams/", json={"name": "Novi", "tag": "NOV"}, headers=headers
    )
    assert resp.status_code == 201
    assert resp.json()["owner_id"] == manager_user.id


async def test_create_team_duplicate_name(client, team):
    headers = await auth_header(client, "testmanager", "manager123")
    resp = await client.post(
        "/teams/", json={"name": "Alpha", "tag": "X"}, headers=headers
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "duplicate"


async def test_create_team_validation_errors_per_field(client, manager_user):
    headers = await auth_header(client, "testmanager", "manager123")
    resp = await client.post(
        "/teams/", json={"name": "", "tag": "PREDUGACKITAG"}, headers=headers
    )
    assert resp.status_code == 422
    fields = {e["field"] for e in resp.json()["errors"]}
    assert fields == {"name", "tag"}


async def test_update_rejects_null(client, team):
    headers = await auth_header(client, "testmanager", "manager123")
    resp = await client.patch(f"/teams/{team.id}", json={"name": None}, headers=headers)
    assert resp.status_code == 422


async def test_update_own_team(client, team):
    headers = await auth_header(client, "testmanager", "manager123")
    resp = await client.patch(f"/teams/{team.id}", json={"tag": "ALF"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["tag"] == "ALF"
    assert resp.json()["name"] == "Alpha"


# --- brisanje --------------------------------------------------------------------


async def test_delete_own_team(client, team):
    headers = await auth_header(client, "testmanager", "manager123")
    resp = await client.delete(f"/teams/{team.id}", headers=headers)
    assert resp.status_code == 204
    resp = await client.get(f"/teams/{team.id}", headers=headers)
    assert resp.status_code == 404


async def test_team_with_registrations_cannot_be_deleted(
    client, db, team, open_tournament
):
    db.add(Registration(tournament_id=open_tournament.id, team_id=team.id))
    await db.commit()
    headers = await auth_header(client, "testmanager", "manager123")
    resp = await client.delete(f"/teams/{team.id}", headers=headers)
    assert resp.status_code == 409
    assert resp.json()["code"] == "has_registrations"
