import pytest
from freezegun import freeze_time

from tests.conftest import BEFORE_DEADLINE, auth_header

NEW_TOURNAMENT = {
    "name": "Novi turnir",
    "max_teams": 8,
    "registration_deadline": "2027-01-15T23:59:00+01:00",
}


@pytest.fixture(autouse=True)
def frozen_now():
    """Zadano vrijeme za ovu datoteku: prije roka iz fixturea i NEW_TOURNAMENT."""
    with freeze_time(BEFORE_DEADLINE):
        yield


def status_url(tournament_id):
    return f"/tournaments/{tournament_id}/status"


# --- vidljivost --------------------------------------------------------------------


async def test_manager_does_not_see_drafts(
    client, manager_user, open_tournament, draft_tournament
):
    headers = await auth_header(client, "testmanager", "manager123")
    resp = await client.get("/tournaments/", headers=headers)
    assert [t["name"] for t in resp.json()] == ["Open Cup"]
    resp = await client.get(f"/tournaments/{draft_tournament.id}", headers=headers)
    assert resp.status_code == 404


async def test_admin_sees_drafts(client, open_tournament, draft_tournament):
    headers = await auth_header(client, "testadmin", "admin123")
    resp = await client.get("/tournaments/", headers=headers)
    assert {t["name"] for t in resp.json()} == {"Open Cup", "Draft Cup"}


async def test_filter_by_status(client, open_tournament, draft_tournament):
    headers = await auth_header(client, "testadmin", "admin123")
    resp = await client.get("/tournaments/?status=draft", headers=headers)
    assert [t["name"] for t in resp.json()] == ["Draft Cup"]


# --- stvaranje -----------------------------------------------------------------------


async def test_admin_creates_tournament_as_draft(client, admin_user):
    headers = await auth_header(client, "testadmin", "admin123")
    resp = await client.post("/tournaments/", json=NEW_TOURNAMENT, headers=headers)
    assert resp.status_code == 201
    assert resp.json()["status"] == "draft"
    assert resp.json()["created_by_id"] == admin_user.id


async def test_deadline_in_past_rejected(client, admin_user):
    headers = await auth_header(client, "testadmin", "admin123")
    body = {**NEW_TOURNAMENT, "registration_deadline": "2027-01-01T12:00:00+01:00"}
    resp = await client.post("/tournaments/", json=body, headers=headers)
    assert resp.status_code == 400
    assert resp.json()["code"] == "invalid_deadline"


async def test_deadline_without_timezone_rejected(client, admin_user):
    headers = await auth_header(client, "testadmin", "admin123")
    body = {**NEW_TOURNAMENT, "registration_deadline": "2027-01-15T23:59:00"}
    resp = await client.post("/tournaments/", json=body, headers=headers)
    assert resp.status_code == 422


# --- prijelazi statusa ---------------------------------------------------------------


async def test_full_status_lifecycle(client, draft_tournament):
    headers = await auth_header(client, "testadmin", "admin123")
    for status in ["registration_open", "ongoing", "finished"]:
        resp = await client.patch(
            status_url(draft_tournament.id), json={"status": status}, headers=headers
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == status


async def test_status_cannot_skip_step(client, draft_tournament):
    headers = await auth_header(client, "testadmin", "admin123")
    resp = await client.patch(
        status_url(draft_tournament.id), json={"status": "ongoing"}, headers=headers
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "invalid_status_transition"


async def test_status_cannot_go_back(client, open_tournament):
    headers = await auth_header(client, "testadmin", "admin123")
    resp = await client.patch(
        status_url(open_tournament.id), json={"status": "draft"}, headers=headers
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "invalid_status_transition"


async def test_manager_cannot_change_status(client, manager_user, open_tournament):
    headers = await auth_header(client, "testmanager", "manager123")
    resp = await client.patch(
        status_url(open_tournament.id), json={"status": "ongoing"}, headers=headers
    )
    assert resp.status_code == 403


# --- izmjena i brisanje ----------------------------------------------------------


async def test_ongoing_tournament_is_locked(client, open_tournament):
    headers = await auth_header(client, "testadmin", "admin123")
    await client.patch(
        status_url(open_tournament.id), json={"status": "ongoing"}, headers=headers
    )
    resp = await client.patch(
        f"/tournaments/{open_tournament.id}", json={"name": "Novo"}, headers=headers
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "tournament_locked"


async def test_only_draft_can_be_deleted(client, open_tournament, draft_tournament):
    headers = await auth_header(client, "testadmin", "admin123")
    resp = await client.delete(f"/tournaments/{open_tournament.id}", headers=headers)
    assert resp.status_code == 409
    assert resp.json()["code"] == "tournament_not_draft"
    resp = await client.delete(f"/tournaments/{draft_tournament.id}", headers=headers)
    assert resp.status_code == 204
