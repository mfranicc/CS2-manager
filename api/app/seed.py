"""Pocetni podatci za razvoj i obranu.

Pokrece se iz mape api/, nakon alembic upgrade head:
    python -m app.seed

Smije se pokrenuti bilo koliko puta: sto vec postoji, ne stvara se ponovno.
"""

import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, engine
from app.core.security import hash_password
from app.models import (
    Player,
    PlayerRole,
    Registration,
    Team,
    Tournament,
    TournamentStatus,
    User,
    UserRole,
)

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

# Dva managera, da se vlasnistvo moze isprobati: manager1 ne smije do timova managera2
# Polja: korisnicko ime, lozinka
MANAGERS = [
    ("manager1", "manager123"),
    ("manager2", "manager123"),
]

# Timovi po manageru; polja: ime, tag, igraci (nadimak, pravo ime, uloga).
# Sastavi prema HLTV-u i Ensigameu, studeni 2026.; None: pravo ime nije provjereno
TEAMS = {
    "manager1": [
        (
            "Team Vitality",
            "VIT",
            [
                ("apEX", "Dan Madesclaire", PlayerRole.igl),
                ("ZywOo", "Mathieu Herbaut", PlayerRole.awper),
                ("ropz", "Robin Kool", PlayerRole.lurker),
                ("flameZ", "Shahar Shushan", PlayerRole.entry),
                ("mezii", "William Merriman", PlayerRole.support),
            ],
        ),
        (
            "Natus Vincere",
            "NAVI",
            [
                ("Aleksib", "Aleksi Virolainen", PlayerRole.igl),
                ("w0nderful", "Ihor Zhdanov", PlayerRole.awper),
                ("iM", "Mihai Ivan", PlayerRole.rifler),
                ("b1t", "Valerii Vakhovskyi", PlayerRole.rifler),
                ("makazze", None, PlayerRole.rifler),
            ],
        ),
        (
            "Falcons",
            "FLC",
            [
                ("karrigan", "Finn Andersen", PlayerRole.igl),
                ("m0NESY", "Ilya Osipov", PlayerRole.awper),
                ("NiKo", "Nikola Kovac", PlayerRole.rifler),
                ("TeSeS", "Rene Madsen", PlayerRole.support),
                ("kyousuke", None, PlayerRole.entry),
            ],
        ),
    ],
    "manager2": [
        (
            "Team Spirit",
            "TS",
            [
                ("sh1ro", "Dmitry Sokolov", PlayerRole.awper),
                ("donk", "Danil Kryshkovets", PlayerRole.entry),
                ("zont1x", "Myroslav Plakhotja", PlayerRole.rifler),
                ("magixx", "Boris Vorobiev", PlayerRole.rifler),
                ("tN1R", None, PlayerRole.rifler),
            ],
        ),
        (
            "MOUZ",
            "MOUZ",
            [
                ("torzsi", "Adam Torzsas", PlayerRole.awper),
                ("xertioN", "Dorian Berman", PlayerRole.entry),
                ("Spinx", "Lotan Giladi", PlayerRole.rifler),
                ("xelex", None, PlayerRole.rifler),
                ("PR", None, PlayerRole.rifler),
            ],
        ),
        (
            "The MongolZ",
            "MGLZ",
            [
                ("bLitz", "Garidmagnai Byambasuren", PlayerRole.igl),
                ("910", "Usukhbayar Banzragch", PlayerRole.awper),
                ("Techno4K", "Sodbayar Munkhbold", PlayerRole.rifler),
                ("nin9", None, PlayerRole.rifler),
                ("cobrazera", None, PlayerRole.entry),
            ],
        ),
    ],
}

# Rokovi su po srednjoeuropskom vremenu, UTC+1
CET = timezone(timedelta(hours=1))

# Po jedan turnir u svakom karakteristicnom stanju; polja: podatci, prijavljeni timovi
TOURNAMENTS = [
    (
        {
            "name": "Zadar Cup 2026",
            "max_teams": 4,
            "registration_deadline": datetime(2026, 10, 1, 23, 59, tzinfo=CET),
            "status": TournamentStatus.finished,
        },
        ["Team Vitality", "Natus Vincere", "Team Spirit", "MOUZ"],
    ),
    (
        {
            "name": "IEM Zagreb 2026",
            "max_teams": 8,
            "registration_deadline": datetime(2026, 12, 15, 23, 59, tzinfo=CET),
            "status": TournamentStatus.registration_open,
        },
        ["Team Vitality", "Team Spirit"],
    ),
    (
        {
            "name": "Split Major 2027",
            "max_teams": 16,
            "registration_deadline": datetime(2027, 3, 1, 23, 59, tzinfo=CET),
            "status": TournamentStatus.draft,
        },
        [],
    ),
]


async def get_or_create_user(
    session: AsyncSession, username: str, password: str, role: UserRole
) -> User:
    result = await session.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(username=username, password_hash=hash_password(password), role=role)
        session.add(user)
        # flush salje upis prije commita, da korisnik dobije id za strani kljuc
        await session.flush()
    return user


async def get_or_create_team(
    session: AsyncSession, name: str, tag: str, owner_id: int
) -> Team:
    result = await session.execute(select(Team).where(Team.name == name))
    team = result.scalar_one_or_none()
    if team is None:
        team = Team(name=name, tag=tag, owner_id=owner_id)
        session.add(team)
        await session.flush()
    return team


async def get_or_create_player(
    session: AsyncSession,
    team_id: int,
    nickname: str,
    real_name: str | None,
    role: PlayerRole,
) -> Player:
    result = await session.execute(select(Player).where(Player.nickname == nickname))
    player = result.scalar_one_or_none()
    if player is None:
        player = Player(
            nickname=nickname, real_name=real_name, role=role, team_id=team_id
        )
        session.add(player)
        await session.flush()
    return player


async def get_or_create_tournament(
    session: AsyncSession, data: dict, created_by_id: int
) -> Tournament:
    result = await session.execute(
        select(Tournament).where(Tournament.name == data["name"])
    )
    tournament = result.scalar_one_or_none()
    if tournament is None:
        tournament = Tournament(**data, created_by_id=created_by_id)
        session.add(tournament)
        await session.flush()
    return tournament


async def get_or_create_registration(
    session: AsyncSession, tournament_id: int, team_id: int
) -> Registration:
    result = await session.execute(
        select(Registration).where(
            Registration.tournament_id == tournament_id,
            Registration.team_id == team_id,
        )
    )
    registration = result.scalar_one_or_none()
    if registration is None:
        registration = Registration(tournament_id=tournament_id, team_id=team_id)
        session.add(registration)
        await session.flush()
    return registration


async def seed() -> None:
    # Jedna transakcija: ili su svi retci upisani, ili nijedan
    async with AsyncSessionLocal() as session, session.begin():
        admin = await get_or_create_user(
            session, ADMIN_USERNAME, ADMIN_PASSWORD, UserRole.admin
        )

        teams_by_name: dict[str, Team] = {}
        for username, password in MANAGERS:
            manager = await get_or_create_user(
                session, username, password, UserRole.manager
            )
            for name, tag, players in TEAMS[username]:
                team = await get_or_create_team(session, name, tag, manager.id)
                teams_by_name[name] = team
                for nickname, real_name, role in players:
                    await get_or_create_player(
                        session, team.id, nickname, real_name, role
                    )

        for data, team_names in TOURNAMENTS:
            tournament = await get_or_create_tournament(session, data, admin.id)
            for team_name in team_names:
                await get_or_create_registration(
                    session, tournament.id, teams_by_name[team_name].id
                )

    await engine.dispose()
    print("Seed gotov.")
    print(f"  admin: {ADMIN_USERNAME} / {ADMIN_PASSWORD}")
    for username, password in MANAGERS:
        team_names = ", ".join(name for name, _, _ in TEAMS[username])
        print(f"  {username} / {password}: {team_names}")
    for data, team_names in TOURNAMENTS:
        print(
            f"  turnir: {data['name']} ({data['status'].value}, "
            f"{len(team_names)}/{data['max_teams']} timova)"
        )


if __name__ == "__main__":
    asyncio.run(seed())
