from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.registration import Registration
from app.models.team import Team


async def get_by_id(db: AsyncSession, team_id: int) -> Team | None:
    return await db.get(Team, team_id)


async def get_by_name(db: AsyncSession, name: str) -> Team | None:
    result = await db.execute(select(Team).where(Team.name == name))
    return result.scalar_one_or_none()


async def get_all(
    db: AsyncSession, owner_id: int | None, limit: int, offset: int
) -> list[Team]:
    # Upit se gradi postupno: vlasnik samo ako je zadan
    stmt = select(Team)
    if owner_id is not None:
        stmt = stmt.where(Team.owner_id == owner_id)
    # Bez order_by stranicenje nije pouzdano: baza sama ne jamci poredak
    stmt = stmt.order_by(Team.id).limit(limit).offset(offset)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create(db: AsyncSession, team: Team) -> Team:
    db.add(team)
    # flush, ne commit: transakciju potvrduje get_db kad cijeli zahtjev prode
    await db.flush()
    return team


async def delete(db: AsyncSession, team: Team) -> None:
    await db.delete(team)
    await db.flush()


async def has_registrations(db: AsyncSession, team_id: int) -> bool:
    stmt = select(exists().where(Registration.team_id == team_id))
    return bool(await db.scalar(stmt))
