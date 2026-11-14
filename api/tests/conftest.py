"""Zajednicka testna infrastruktura.

Testovi rade nad zasebnom bazom cs2manager_test na istom PostgreSQL
posluzitelju, pa razvojni podatci u cs2manager ostaju netaknuti.
Prije pokretanja: docker compose up -d
"""

import asyncio
from collections.abc import AsyncGenerator
from datetime import datetime, timezone

import bcrypt
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import make_url, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.deps import get_db
from app.main import create_app
from app.models import (
    Base,
    Player,
    PlayerRole,
    Team,
    Tournament,
    TournamentStatus,
    User,
    UserRole,
)


def _test_database_url() -> str:
    if settings.test_database_url:
        return settings.test_database_url
    url = make_url(settings.database_url)
    url = url.set(database=f"{url.database}_test")
    return url.render_as_string(hide_password=False)


TEST_DATABASE_URL = _test_database_url()

# NullPool: svaki test ima svoju petlju dogadaja, pa veze ne smiju prezivjeti test
engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
TestSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

# Rok prijave za otvoreni turnir iz fixturea; testovi zamrzavaju vrijeme oko njega
DEADLINE = datetime(2027, 1, 15, 22, 59, tzinfo=timezone.utc)
BEFORE_DEADLINE = "2027-01-10 12:00:00"
AFTER_DEADLINE = "2027-01-16 12:00:00"


async def _prepare_database() -> None:
    url = make_url(TEST_DATABASE_URL)
    server = create_async_engine(
        url.set(database="postgres"), isolation_level="AUTOCOMMIT", poolclass=NullPool
    )
    async with server.connect() as conn:
        exists = await conn.scalar(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": url.database},
        )
        if not exists:
            await conn.execute(text(f'CREATE DATABASE "{url.database}"'))
    await server.dispose()

    # Shema iz modela, svaki put iznova
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


@pytest.fixture(scope="session", autouse=True)
def test_database():
    asyncio.run(_prepare_database())


@pytest.fixture(autouse=True)
async def clean_tables():
    """Svaki test pocinje od praznih tablica."""
    tables = ", ".join(table.name for table in Base.metadata.sorted_tables)
    async with engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


async def _get_test_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """HTTP klijent nad aplikacijom, bez pokretanja posluzitelja."""
    app = create_app()
    app.dependency_overrides[get_db] = _get_test_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    """Sesija za pripremu podataka izravno u bazi."""
    async with TestSessionLocal() as session:
        yield session


def fast_hash(password: str) -> str:
    # Faktor rada 4 umjesto zadanih 12: hash je jednako valjan, a testovi brzi
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=4)).decode()


async def auth_header(client: AsyncClient, username: str, password: str) -> dict:
    resp = await client.post(
        "/auth/login", json={"username": username, "password": password}
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _create_user(
    db: AsyncSession, username: str, password: str, role: UserRole
) -> User:
    user = User(username=username, password_hash=fast_hash(password), role=role)
    db.add(user)
    await db.commit()
    return user


async def create_team(
    db: AsyncSession, owner: User, name: str, players: int = 5
) -> Team:
    """Tim s trazenim brojem igraca, upisan izravno u bazu, mimo API-ja."""
    team = Team(name=name, tag=name[:4].upper(), owner_id=owner.id)
    db.add(team)
    await db.flush()
    for number in range(players):
        db.add(
            Player(
                nickname=f"{name}-{number + 1}",
                role=PlayerRole.rifler,
                team_id=team.id,
            )
        )
    await db.commit()
    return team


@pytest.fixture
async def admin_user(db: AsyncSession) -> User:
    """Admin: testadmin / admin123."""
    return await _create_user(db, "testadmin", "admin123", UserRole.admin)


@pytest.fixture
async def manager_user(db: AsyncSession) -> User:
    """Manager: testmanager / manager123."""
    return await _create_user(db, "testmanager", "manager123", UserRole.manager)


@pytest.fixture
async def rival_user(db: AsyncSession) -> User:
    """Drugi manager, za provjere vlasnistva: rival / rival123."""
    return await _create_user(db, "rival", "rival123", UserRole.manager)


@pytest.fixture
async def team(db: AsyncSession, manager_user: User) -> Team:
    """Tim managera testmanager s punom postavom od 5 igraca."""
    return await create_team(db, manager_user, "Alpha")


@pytest.fixture
async def rival_team(db: AsyncSession, rival_user: User) -> Team:
    """Tim managera rival s punom postavom od 5 igraca."""
    return await create_team(db, rival_user, "Bravo")


async def _create_tournament(
    db: AsyncSession, admin: User, name: str, status: TournamentStatus
) -> Tournament:
    tournament = Tournament(
        name=name,
        max_teams=4,
        registration_deadline=DEADLINE,
        status=status,
        created_by_id=admin.id,
    )
    db.add(tournament)
    await db.commit()
    return tournament


@pytest.fixture
async def open_tournament(db: AsyncSession, admin_user: User) -> Tournament:
    """Turnir s otvorenim prijavama, 4 mjesta, rok 15.01.2027. u 23:59 CET."""
    return await _create_tournament(
        db, admin_user, "Open Cup", TournamentStatus.registration_open
    )


@pytest.fixture
async def draft_tournament(db: AsyncSession, admin_user: User) -> Tournament:
    """Turnir u pripremi, vidljiv samo adminu."""
    return await _create_tournament(db, admin_user, "Draft Cup", TournamentStatus.draft)
