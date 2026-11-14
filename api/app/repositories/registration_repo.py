from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.registration import Registration
from app.models.team import Team


async def get_by_id(db: AsyncSession, registration_id: int) -> Registration | None:
    # Tim se dohvaca unaprijed: u asinkronom radu lijeno ucitavanje
    # registration.team podize iznimku tek pri popunjavanju odgovora
    stmt = (
        select(Registration)
        .options(selectinload(Registration.team))
        .where(Registration.id == registration_id)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_by_tournament_and_team(
    db: AsyncSession, tournament_id: int, team_id: int
) -> Registration | None:
    stmt = select(Registration).where(
        Registration.tournament_id == tournament_id,
        Registration.team_id == team_id,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_for_tournament(
    db: AsyncSession,
    tournament_id: int,
    owner_id: int | None,
    limit: int,
    offset: int,
) -> list[Registration]:
    # selectinload: dva upita ukupno, jedan za prijave i jedan za sve njihove
    # timove. Bez njega slijedi po jedan upit za svaku prijavu: problem N+1
    stmt = (
        select(Registration)
        .options(selectinload(Registration.team))
        .where(Registration.tournament_id == tournament_id)
    )
    if owner_id is not None:
        # Suzavanje u upitu: tude prijave ni ne izlaze iz baze
        stmt = stmt.join(Registration.team).where(Team.owner_id == owner_id)
    stmt = stmt.order_by(Registration.id).limit(limit).offset(offset)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create(db: AsyncSession, registration: Registration) -> Registration:
    db.add(registration)
    await db.flush()
    # Ponovno ucitavanje s timom, da ga odgovor moze procitati
    return await get_by_id(db, registration.id)


async def delete(db: AsyncSession, registration: Registration) -> None:
    await db.delete(registration)
    await db.flush()
