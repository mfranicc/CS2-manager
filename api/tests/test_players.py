from tests.conftest import auth_header, create_team


def url(team, player_id=None):
    base = f"/teams/{team.id}/players/"
    return base if player_id is None else f"{base}{player_id}"


async def test_list_players_of_own_team(client, team):
    headers = await auth_header(client, "testmanager", "manager123")
    resp = await client.get(url(team), headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 5


async def test_filter_players_by_role(client, team):
    headers = await auth_header(client, "testmanager", "manager123")
    resp = await client.get(url(team) + "?role=awper", headers=headers)
    assert resp.status_code == 200
    # Igraci iz fixturea su svi rifleri
    assert resp.json() == []


async def test_manager_cannot_list_other_team_players(client, team, rival_team):
    headers = await auth_header(client, "testmanager", "manager123")
    resp = await client.get(url(rival_team), headers=headers)
    assert resp.status_code == 403


async def test_manager_cannot_add_player_to_other_team(client, team, rival_team):
    headers = await auth_header(client, "testmanager", "manager123")
    resp = await client.post(
        url(rival_team), json={"nickname": "Uljez", "role": "rifler"}, headers=headers
    )
    assert resp.status_code == 403


async def test_player_of_other_team_not_found_under_this_team(
    client, db, manager_user, team
):
    other = await create_team(db, manager_user, "Charlie", players=1)
    headers = await auth_header(client, "testmanager", "manager123")
    other_player_id = (await client.get(url(other), headers=headers)).json()[0]["id"]
    # Igrac postoji, ali ne pod adresom ovog tima
    resp = await client.get(url(team, other_player_id), headers=headers)
    assert resp.status_code == 404


async def test_create_player(client, db, manager_user):
    small = await create_team(db, manager_user, "Mali", players=0)
    headers = await auth_header(client, "testmanager", "manager123")
    resp = await client.post(
        url(small),
        json={"nickname": "s1mple", "real_name": "Oleksandr", "role": "awper"},
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["team_id"] == small.id
    assert resp.json()["role"] == "awper"


async def test_invalid_role_is_validation_error(client, team):
    headers = await auth_header(client, "testmanager", "manager123")
    resp = await client.post(
        url(team), json={"nickname": "Kuhar", "role": "kuhar"}, headers=headers
    )
    assert resp.status_code == 422
    assert resp.json()["errors"][0]["field"] == "role"


async def test_duplicate_nickname(client, team):
    headers = await auth_header(client, "testmanager", "manager123")
    resp = await client.post(
        url(team), json={"nickname": "Alpha-1", "role": "rifler"}, headers=headers
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "duplicate"


async def test_team_cannot_have_more_than_seven_players(client, db, manager_user):
    full = await create_team(db, manager_user, "Puni", players=7)
    headers = await auth_header(client, "testmanager", "manager123")
    resp = await client.post(
        url(full), json={"nickname": "Osmi", "role": "rifler"}, headers=headers
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "team_full"


async def test_sixth_and_seventh_player_allowed(client, team):
    headers = await auth_header(client, "testmanager", "manager123")
    for nickname in ["Sub1", "Sub2"]:
        resp = await client.post(
            url(team), json={"nickname": nickname, "role": "support"}, headers=headers
        )
        assert resp.status_code == 201


async def test_update_and_delete_player(client, team):
    headers = await auth_header(client, "testmanager", "manager123")
    player_id = (await client.get(url(team), headers=headers)).json()[0]["id"]

    resp = await client.patch(
        url(team, player_id), json={"role": "igl"}, headers=headers
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "igl"

    resp = await client.delete(url(team, player_id), headers=headers)
    assert resp.status_code == 204
    resp = await client.get(url(team, player_id), headers=headers)
    assert resp.status_code == 404
