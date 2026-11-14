import pytest
from freezegun import freeze_time

from app.models import Registration
from tests.conftest import AFTER_DEADLINE, BEFORE_DEADLINE, auth_header, create_team


@pytest.fixture(autouse=True)
def before_deadline():
    """Zadano vrijeme za ovu datoteku: prije roka turnira iz fixturea.

    Rok je 15.01.2027.; bez zamrzavanja ishod testa ovisio bi o danu pokretanja.
    """
    with freeze_time(BEFORE_DEADLINE):
        yield


def url(tournament, registration_id=None):
    base = f"/tournaments/{tournament.id}/registrations/"
    return base if registration_id is None else f"{base}{registration_id}"


async def register(db, tournament, team):
    """Prijava upisana izravno u bazu, mimo API-ja."""
    registration = Registration(tournament_id=tournament.id, team_id=team.id)
    db.add(registration)
    await db.commit()
    return registration


# --- uspjesna prijava ---------------------------------------------------------------


async def test_manager_registers_own_team(client, team, open_tournament):
    headers = await auth_header(client, "testmanager", "manager123")
    resp = await client.post(
        url(open_tournament), json={"team_id": team.id}, headers=headers
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["tournament_id"] == open_tournament.id
    # Povezani zapis u odgovoru, suzeno na ime i tag
    assert body["team"] == {"name": "Alpha", "tag": "ALPH"}


# --- vlasnistvo i uloge --------------------------------------------------------------


async def test_manager_cannot_register_other_team(
    client, team, rival_team, open_tournament
):
    headers = await auth_header(client, "testmanager", "manager123")
    # Tuda oznaka stize u tijelu zahtjeva, ne u adresi
    resp = await client.post(
        url(open_tournament), json={"team_id": rival_team.id}, headers=headers
    )
    assert resp.status_code == 403


async def test_admin_cannot_register_team(client, team, open_tournament):
    headers = await auth_header(client, "testadmin", "admin123")
    resp = await client.post(
        url(open_tournament), json={"team_id": team.id}, headers=headers
    )
    assert resp.status_code == 403


async def test_manager_sees_only_own_registrations(
    client, db, team, rival_team, open_tournament
):
    await register(db, open_tournament, team)
    await register(db, open_tournament, rival_team)
    headers = await auth_header(client, "testmanager", "manager123")
    resp = await client.get(url(open_tournament), headers=headers)
    assert [r["team"]["name"] for r in resp.json()] == ["Alpha"]


async def test_manager_cannot_withdraw_other_registration(
    client, db, team, rival_team, open_tournament
):
    registration = await register(db, open_tournament, rival_team)
    headers = await auth_header(client, "testmanager", "manager123")
    resp = await client.delete(url(open_tournament, registration.id), headers=headers)
    assert resp.status_code == 403


# --- poslovna pravila: rok ---------------------------------------------------------


async def test_registration_after_deadline_rejected(client, team, open_tournament):
    with freeze_time(AFTER_DEADLINE):
        headers = await auth_header(client, "testmanager", "manager123")
        resp = await client.post(
            url(open_tournament), json={"team_id": team.id}, headers=headers
        )
    assert resp.status_code == 409
    # Kod pogreske potvrduje da je razlog odbijanja rok, a ne nesto drugo
    assert resp.json()["code"] == "registration_closed"


async def test_registration_one_minute_before_deadline_allowed(
    client, team, open_tournament
):
    with freeze_time("2027-01-15 22:58:00"):
        headers = await auth_header(client, "testmanager", "manager123")
        resp = await client.post(
            url(open_tournament), json={"team_id": team.id}, headers=headers
        )
    assert resp.status_code == 201


async def test_withdrawal_after_deadline_rejected(client, db, team, open_tournament):
    registration = await register(db, open_tournament, team)
    with freeze_time(AFTER_DEADLINE):
        headers = await auth_header(client, "testmanager", "manager123")
        resp = await client.delete(
            url(open_tournament, registration.id), headers=headers
        )
    assert resp.status_code == 409
    assert resp.json()["code"] == "registration_closed"


async def test_withdrawal_before_deadline_allowed(client, db, team, open_tournament):
    registration = await register(db, open_tournament, team)
    headers = await auth_header(client, "testmanager", "manager123")
    resp = await client.delete(url(open_tournament, registration.id), headers=headers)
    assert resp.status_code == 204


# --- poslovna pravila: status, kapacitet, sastav -------------------------------------


async def test_registration_closed_when_not_open(client, team, open_tournament):
    admin = await auth_header(client, "testadmin", "admin123")
    await client.patch(
        f"/tournaments/{open_tournament.id}/status",
        json={"status": "ongoing"},
        headers=admin,
    )
    headers = await auth_header(client, "testmanager", "manager123")
    resp = await client.post(
        url(open_tournament), json={"team_id": team.id}, headers=headers
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "registration_not_open"


async def test_cannot_register_to_draft(client, team, draft_tournament):
    headers = await auth_header(client, "testmanager", "manager123")
    resp = await client.post(
        url(draft_tournament), json={"team_id": team.id}, headers=headers
    )
    assert resp.status_code == 404


async def test_tournament_full(client, db, admin_user, team, open_tournament):
    # Turnir iz fixturea ima 4 mjesta; popunjavaju ih timovi drugog managera
    for name in ["F1", "F2", "F3", "F4"]:
        other = await create_team(db, admin_user, name)
        await register(db, open_tournament, other)
    headers = await auth_header(client, "testmanager", "manager123")
    resp = await client.post(
        url(open_tournament), json={"team_id": team.id}, headers=headers
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "tournament_full"


async def test_team_needs_five_players(client, db, manager_user, open_tournament):
    small = await create_team(db, manager_user, "Mali", players=4)
    headers = await auth_header(client, "testmanager", "manager123")
    resp = await client.post(
        url(open_tournament), json={"team_id": small.id}, headers=headers
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "not_enough_players"


async def test_duplicate_registration(client, db, team, open_tournament):
    await register(db, open_tournament, team)
    headers = await auth_header(client, "testmanager", "manager123")
    resp = await client.post(
        url(open_tournament), json={"team_id": team.id}, headers=headers
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "duplicate"


async def test_capacity_cannot_drop_below_registrations(
    client, db, admin_user, open_tournament
):
    for name in ["C1", "C2", "C3"]:
        other = await create_team(db, admin_user, name)
        await register(db, open_tournament, other)
    headers = await auth_header(client, "testadmin", "admin123")
    resp = await client.patch(
        f"/tournaments/{open_tournament.id}", json={"max_teams": 2}, headers=headers
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "max_teams_too_low"
    resp = await client.patch(
        f"/tournaments/{open_tournament.id}", json={"max_teams": 3}, headers=headers
    )
    assert resp.status_code == 200
